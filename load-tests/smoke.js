// Smoke test.
//
// A short, low volume run to confirm the platform is healthy before
// committing to a full scenario. Worth running first on capture day, when
// cluster time costs money.

import http from 'k6/http';
import { check } from 'k6';
import {
  BASE_URL,
  login,
  authHeaders,
  idempotencyKey,
  paymentBody,
  pickBusiness,
} from './lib.js';

export const options = {
  vus: 5,
  duration: '1m',
  thresholds: {
    'http_req_failed': ['rate<0.01'],
    'http_req_duration': ['p(95)<500'],
  },
};

export function setup() {
  const business = pickBusiness();
  const token = login(business);
  if (!token) throw new Error('setup failed: could not authenticate');
  return { token, accountId: business.account_id };
}

export default function (data) {
  const health = http.get(`${BASE_URL}/health`, { tags: { name: 'health' } });
  check(health, { 'gateway healthy': (r) => r.status === 200 });

  const balance = http.get(
    `${BASE_URL}/v1/accounts/${data.accountId}/balance`,
    { headers: authHeaders(data.token), tags: { name: 'read_balance' } }
  );
  check(balance, { 'balance returned': (r) => r.status === 200 });

  const payment = http.post(
    `${BASE_URL}/v1/payments`,
    paymentBody(data.accountId),
    { headers: authHeaders(data.token, idempotencyKey()), tags: { name: 'submit_payment' } }
  );
  check(payment, { 'payment accepted': (r) => r.status === 201 || r.status === 202 });
}
