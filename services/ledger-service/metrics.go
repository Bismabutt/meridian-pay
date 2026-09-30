package main

// Ledger metrics.
//
// The ledger is the authoritative record of how the pooled balance divides
// between customers. These metrics measure write throughput, the integrity
// check that rejects unbalanced transactions, and reconciliation status.

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

var (
	// Write throughput, by outcome. Rejected writes are the double entry
	// validation refusing a transaction whose legs do not sum to zero.
	ledgerEntriesWritten = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "ledger_entries_written_total",
			Help: "Ledger entries written, by outcome",
		},
		[]string{"outcome"}, // written | rejected_unbalanced | failed
	)

	ledgerTransactionsTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "ledger_transactions_total",
			Help: "Ledger transactions, by outcome",
		},
		[]string{"outcome"},
	)

	ledgerWriteDuration = promauto.NewHistogram(
		prometheus.HistogramOpts{
			Name:    "ledger_write_duration_seconds",
			Help:    "Time to write a balanced double entry transaction",
			Buckets: []float64{0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0},
		},
	)

	// Balance derivation. There is no balance column; balance is summed
	// from entries, so this is worth measuring as the table grows.
	ledgerBalanceQueryDuration = promauto.NewHistogram(
		prometheus.HistogramOpts{
			Name:    "ledger_balance_query_duration_seconds",
			Help:    "Time to derive an account balance by summing entries",
			Buckets: []float64{0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5},
		},
	)

	// Reconciliation. Variance must be zero: the sum of all customer
	// balances must equal the pooled balance held at the partner bank.
	// A non-zero value here is a safeguarding incident, not a warning.
	ledgerReconciliationVariance = promauto.NewGauge(
		prometheus.GaugeOpts{
			Name: "ledger_reconciliation_variance_minor",
			Help: "Difference between the ledger total and the partner pooled balance",
		},
	)

	ledgerReconciliationLastRun = promauto.NewGauge(
		prometheus.GaugeOpts{
			Name: "ledger_reconciliation_last_run_timestamp_seconds",
			Help: "Unix timestamp of the last completed reconciliation",
		},
	)

	// HTTP RED metrics
	httpRequestsTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "http_requests_total",
			Help: "HTTP requests received",
		},
		[]string{"service", "method", "path", "status"},
	)

	httpRequestDuration = promauto.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "http_request_duration_seconds",
			Help:    "Time from request received to response sent",
			Buckets: []float64{0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5},
		},
		[]string{"service", "method", "path"},
	)
)
