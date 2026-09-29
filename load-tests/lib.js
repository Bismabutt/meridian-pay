// Shared helpers for the Meridian Pay load scenarios.
//
// Test businesses are seeded before the run by scripts/seed_data.py, so the
// scenarios measure payment throughput rather than registration throughput.

import http from 'k6/http';
import { check } from 'k6';
import { SharedArray } from 'k6/data';
import { randomIntBetween } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';

export const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Loaded once per test run and shared across all virtual users, rather than
// once per VU, which would multiply memory by the VU count.
export const businesses = new SharedArray('businesses', function () {
  return JSON.parse(open('./test-businesses.json'));
});

export function login(business) {
  const res = http.post(
    `${BASE_URL}/v1/auth/login`,
    JSON.stringify({ email: business.email, password: business.password }),
    { headers: { 'Content-Type': 'application/json' }, tags: { name: 'login' } }
  );

  check(res, { 'login succeeded': (r) => r.status === 200 });

  if (res.status !== 200) return null;
  return res.json('access_token');
}

export function authHeaders(token, idempotencyKey) {
  const h = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };
  if (idempotencyKey) h['Idempotency-Key'] = idempotencyKey;
  return h;
}

// A unique key per payment. The platform rejects duplicates, so reusing a key
// would measure the idempotency guard rather than payment throughput.
export function idempotencyKey() {
  return `k6-${__VU}-${__ITER}-${Date.now()}-${randomIntBetween(1, 1e6)}`;
}

export function paymentBody(fromAccount) {
  return JSON.stringify({
    from_account_id: fromAccount,
    to_sort_code: '04-00-04',
    to_account_number: String(randomIntBetween(10000000, 99999999)),
    to_name: 'Supplier Ltd',
    amount_minor: randomIntBetween(1000, 500000),
    currency: 'GBP',
    reference: `INV-${randomIntBetween(1000, 9999)}`,
  });
}

export function pickBusiness() {
  return businesses[randomIntBetween(0, businesses.length - 1)];
}
