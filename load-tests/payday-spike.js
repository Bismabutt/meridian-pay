// Payday spike.
//
// Reproduces the traffic pattern described in discovery: a 12x rise within
// fifteen minutes on the first working morning after month end, when every
// business runs payroll and supplier runs at once.
//
// Baseline 40 payments/sec, peak 500. The interesting question is not whether
// the platform survives the peak, but whether customer visible latency holds
// while it scales.

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend, Rate, Counter } from 'k6/metrics';
import {
  PAYMENT_URL,
  BASE_URL,
  login,
  authHeaders,
  idempotencyKey,
  paymentBody,
  pickBusiness,
} from './lib.js';

// Custom metrics, reported alongside the platform's own.
const paymentDuration = new Trend('payment_duration_ms', true);
const paymentSuccess = new Rate('payment_success_rate');
const paymentsSubmitted = new Counter('payments_submitted');
const balanceReads = new Counter('balance_reads');

export const options = {
  scenarios: {
    // Read traffic. Balance checks outnumber payments roughly six to one,
    // so this runs continuously underneath the payment load.
    balance_reads: {
      executor: 'constant-arrival-rate',
      rate: 300,
      timeUnit: '1s',
      duration: '32m',
      preAllocatedVUs: 100,
      maxVUs: 400,
      exec: 'readBalance',
    },

    // Payments. Ramps from baseline to peak and back.
    payday: {
      executor: 'ramping-arrival-rate',
      startRate: 40,
      timeUnit: '1s',
      preAllocatedVUs: 100,
      maxVUs: 800,
      exec: 'submitPayment',
      stages: [
        { duration: '5m',  target: 40 },   // baseline, establishes the floor
        { duration: '15m', target: 500 },  // the spike
        { duration: '7m',  target: 500 },  // hold at peak
        { duration: '5m',  target: 40 },   // decline
      ],
    },
  },

  // The platform fails the run if these are breached. p95 at 300ms is the
  // stated objective; anything above 1 percent failure is unacceptable for
  // payment submission.
  thresholds: {
    'payment_duration_ms': ['p(95)<300', 'p(99)<800'],
    'payment_success_rate': ['rate>0.99'],
    'http_req_failed': ['rate<0.01'],
  },
};

export function setup() {
  const business = pickBusiness();
  const token = login(business);
  if (!token) throw new Error('setup failed: could not authenticate');
  return { token, accountId: business.account_id };
}

export function submitPayment(data) {
  const started = Date.now();

  const res = http.post(
    `${BASE_URL}/v1/payments`,
    paymentBody(data.accountId, idempotencyKey()),
    {
      headers: authHeaders(data.token, idempotencyKey()),
      tags: { name: 'submit_payment' },
    }
  );

  const elapsed = Date.now() - started;
  paymentDuration.add(elapsed);
  paymentsSubmitted.add(1);

  const ok = check(res, {
    'payment accepted': (r) => r.status === 201 || r.status === 202,
    'response has payment id': (r) => r.json('id') !== undefined,
  });

  paymentSuccess.add(ok);
}

export function readBalance(data) {
  const res = http.get(
    `${BASE_URL}/v1/accounts/${data.accountId}/balance`,
    {
      headers: authHeaders(data.token),
      tags: { name: 'read_balance' },
    }
  );

  balanceReads.add(1);
  check(res, { 'balance returned': (r) => r.status === 200 });
}
