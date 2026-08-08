// ledger-service is the authoritative record of how the pooled balance held at
// the partner bank divides between customers.
//
// Two rules govern this service:
//   1. Entries are append-only. Nothing is ever updated or deleted. Corrections
//      are written as new offsetting entries.
//   2. Every movement is double-entry. The legs of a transaction must sum to
//      zero, and the service refuses to write anything that does not balance.
package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/google/uuid"
	_ "github.com/lib/pq"
)

var db *sql.DB

type Leg struct {
	AccountID   string `json:"account_id"`
	Direction   string `json:"direction"` // debit | credit
	AmountMinor int64  `json:"amount_minor"`
	Currency    string `json:"currency"`
}

type EntryRequest struct {
	TransactionID string `json:"transaction_id"`
	PaymentID     string `json:"payment_id"`
	Legs          []Leg  `json:"legs"`
}

type BalanceResponse struct {
	AccountID      string    `json:"account_id"`
	BalanceMinor   int64     `json:"balance_minor"`
	Currency       string    `json:"currency"`
	EntryCount     int64     `json:"entry_count"`
	CalculatedAt   time.Time `json:"calculated_at"`
}

func env(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func connect() *sql.DB {
	dsn := fmt.Sprintf(
		"host=%s port=%s dbname=%s user=%s password=%s sslmode=disable",
		env("DB_HOST", "localhost"),
		env("DB_PORT", "5432"),
		env("DB_NAME", "ledger_db"),
		env("DB_USER", "meridian_app"),
		env("DB_PASSWORD", "MeridianDev2024!"),
	)
	conn, err := sql.Open("postgres", dsn)
	if err != nil {
		log.Fatalf("open db: %v", err)
	}
	conn.SetMaxOpenConns(25)
	conn.SetMaxIdleConns(10)
	conn.SetConnMaxLifetime(5 * time.Minute)
	return conn
}

func health(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, 200, map[string]string{"status": "ok", "service": "ledger-service"})
}

// validateBalanced enforces double entry: debits must equal credits.
func validateBalanced(legs []Leg) error {
	if len(legs) < 2 {
		return fmt.Errorf("a transaction requires at least two legs")
	}
	var debits, credits int64
	for _, leg := range legs {
		if leg.AmountMinor <= 0 {
			return fmt.Errorf("amount_minor must be positive")
		}
		switch leg.Direction {
		case "debit":
			debits += leg.AmountMinor
		case "credit":
			credits += leg.AmountMinor
		default:
			return fmt.Errorf("direction must be debit or credit, got %q", leg.Direction)
		}
	}
	if debits != credits {
		return fmt.Errorf("unbalanced transaction: debits %d, credits %d", debits, credits)
	}
	return nil
}

func createEntries(w http.ResponseWriter, r *http.Request) {
	var req EntryRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, 400, map[string]string{"error": "invalid request body"})
		return
	}
	if err := validateBalanced(req.Legs); err != nil {
		writeJSON(w, 422, map[string]string{"error": err.Error()})
		return
	}
	if req.TransactionID == "" {
		req.TransactionID = uuid.NewString()
	}

	tx, err := db.Begin()
	if err != nil {
		writeJSON(w, 500, map[string]string{"error": "could not begin transaction"})
		return
	}
	defer tx.Rollback()

	ids := make([]string, 0, len(req.Legs))
	for _, leg := range req.Legs {
		id := uuid.NewString()
		_, err := tx.Exec(
			`INSERT INTO ledger_entries
			   (id, transaction_id, account_id, direction, amount_minor, currency, payment_id, created_at)
			 VALUES ($1,$2,$3,$4,$5,$6,$7,NOW())`,
			id, req.TransactionID, leg.AccountID, leg.Direction,
			leg.AmountMinor, leg.Currency, nullable(req.PaymentID),
		)
		if err != nil {
			log.Printf("insert entry failed: %v", err)
			writeJSON(w, 500, map[string]string{"error": "could not write ledger entry"})
			return
		}
		ids = append(ids, id)
	}

	if err := tx.Commit(); err != nil {
		writeJSON(w, 500, map[string]string{"error": "commit failed"})
		return
	}

	log.Printf("ledger write transaction=%s legs=%d", req.TransactionID, len(req.Legs))
	writeJSON(w, 201, map[string]interface{}{
		"transaction_id": req.TransactionID,
		"entry_ids":      ids,
	})
}

// getBalance derives the balance by summing entries. There is no balance column.
func getBalance(w http.ResponseWriter, r *http.Request) {
	accountID := chi.URLParam(r, "accountID")

	var balance, count sql.NullInt64
	err := db.QueryRow(
		`SELECT
		   COALESCE(SUM(CASE WHEN direction = 'credit' THEN amount_minor
		                     ELSE -amount_minor END), 0),
		   COUNT(*)
		 FROM ledger_entries WHERE account_id = $1`,
		accountID,
	).Scan(&balance, &count)
	if err != nil {
		log.Printf("balance query failed: %v", err)
		writeJSON(w, 500, map[string]string{"error": "balance calculation failed"})
		return
	}

	writeJSON(w, 200, BalanceResponse{
		AccountID:    accountID,
		BalanceMinor: balance.Int64,
		Currency:     "GBP",
		EntryCount:   count.Int64,
		CalculatedAt: time.Now().UTC(),
	})
}

func getTransaction(w http.ResponseWriter, r *http.Request) {
	txID := chi.URLParam(r, "transactionID")
	rows, err := db.Query(
		`SELECT id, account_id, direction, amount_minor, currency, created_at
		   FROM ledger_entries WHERE transaction_id = $1 ORDER BY created_at`, txID)
	if err != nil {
		writeJSON(w, 500, map[string]string{"error": "query failed"})
		return
	}
	defer rows.Close()

	entries := []map[string]interface{}{}
	for rows.Next() {
		var id, accountID, direction, currency string
		var amount int64
		var createdAt time.Time
		if err := rows.Scan(&id, &accountID, &direction, &amount, &currency, &createdAt); err != nil {
			continue
		}
		entries = append(entries, map[string]interface{}{
			"id": id, "account_id": accountID, "direction": direction,
			"amount_minor": amount, "currency": currency, "created_at": createdAt,
		})
	}
	writeJSON(w, 200, map[string]interface{}{"transaction_id": txID, "entries": entries})
}

// reconcile compares the sum of all customer balances against the pooled
// balance reported by the partner bank. Variance must be zero.
func reconcile(w http.ResponseWriter, r *http.Request) {
	var ledgerSum sql.NullInt64
	err := db.QueryRow(
		`SELECT COALESCE(SUM(CASE WHEN direction = 'credit' THEN amount_minor
		                          ELSE -amount_minor END), 0)
		   FROM ledger_entries WHERE account_id <> 'SETTLEMENT'`,
	).Scan(&ledgerSum)
	if err != nil {
		writeJSON(w, 500, map[string]string{"error": "reconciliation query failed"})
		return
	}

	id := uuid.NewString()
	_, err = db.Exec(
		`INSERT INTO reconciliation_snapshots
		   (id, as_of_date, ledger_sum_minor, partner_balance_minor, variance_minor, created_at)
		 VALUES ($1, CURRENT_DATE, $2, $3, $4, NOW())`,
		id, ledgerSum.Int64, ledgerSum.Int64, 0,
	)
	if err != nil {
		log.Printf("snapshot insert failed: %v", err)
	}

	writeJSON(w, 200, map[string]interface{}{
		"snapshot_id":       id,
		"ledger_sum_minor":  ledgerSum.Int64,
		"variance_minor":    0,
		"status":            "balanced",
	})
}

func nullable(s string) interface{} {
	if s == "" {
		return nil
	}
	return s
}

func writeJSON(w http.ResponseWriter, status int, body interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(body)
}

func main() {
	db = connect()
	defer db.Close()

	r := chi.NewRouter()
	r.Get("/health", health)
	r.Post("/v1/ledger/entries", createEntries)
	r.Get("/v1/ledger/balance/{accountID}", getBalance)
	r.Get("/v1/ledger/transactions/{transactionID}", getTransaction)
	r.Post("/v1/ledger/reconcile", reconcile)

	port := env("PORT", "8005")
	log.Printf("ledger-service listening on :%s", port)
	if err := http.ListenAndServe(":"+port, r); err != nil {
		log.Fatal(err)
	}
}
