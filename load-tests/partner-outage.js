// Partner bank outage drill.
//
// Discovery established that the partner bank had two thirty minute outages
// in six months, and that during those windows payments were rejected
// outright. The design decision was to queue and retry rather than reject,
// because a customer who sees a failure submits again, which is how
// duplicates happen.
//
// This scenario holds steady load while the partner bank is taken down
// mid run using its /admin/outage endpoint. The measurement that matters is
// that payment acceptance continues, pending count rises, and nothing is lost.

import http from 'k6/http';
import { check } from 'k6';
import { Trend, Rate, Counter } from 'k6/metrics';
import {
  BASE_URL,
  login,
  authHeaders,
  idempotencyKey,
  paymentBody,
  pickBusiness,
} from './lib.js';

const paymentDuration = new Trend('payment_duration_ms', true);
const paymentAccepted = new Rate('payment_accepted_rate');
const paymentsQueued = new Counter('payments_queued');

export const options = {
  scenarios: {
    steady: {
      executor: 'constant-arrival-rate',
      rate: 60,
      timeUnit: '1s',
      duration: '12m',
      preAllocatedVUs: 50,
      maxVUs: 200,
      exec: 'submitPayment',
    },
  },

  // Acceptance must hold even while the partner is down. Latency is allowed
  // to rise, because the platform is retrying behind the scenes, but a
  // customer must never be told their payment failed.
  thresholds: {
    'payment_accepted_rate': ['rate>0.99'],
    'payment_duration_ms': ['p(95)<2000'],
  },
};

export function setup() {
  const business = pickBusiness();
  const token = login(business);
  if (!token) throw new Error('setup failed: could not authenticate');

  console.log('');
  console.log('  Drill timeline');
  console.log('  0:00 to 4:00   steady state, partner healthy');
  console.log('  4:00           take the partner bank down:');
  console.log('                 curl -X POST $PARTNER_URL/admin/outage -d \'{"enabled":true}\'');
  console.log('  4:00 to 8:00   outage window, payments must still be accepted');
  console.log('  8:00           restore the partner bank:');
  console.log('                 curl -X POST $PARTNER_URL/admin/outage -d \'{"enabled":false}\'');
  console.log('  8:00 to 12:00  recovery, pending queue drains to zero');
  console.log('');

  return { token, accountId: business.account_id };
}

export function submitPayment(data) {
  const started = Date.now();

  const res = http.post(
    `${BASE_URL}/v1/payments`,
    paymentBody(data.accountId),
    {
      headers: authHeaders(data.token, idempotencyKey()),
      tags: { name: 'submit_payment' },
      timeout: '10s',
    }
  );

  paymentDuration.add(Date.now() - started);

  // 201 accepted and cleared, 202 accepted and queued. Both are successes
  // from the customer's point of view: the money will move.
  const accepted = check(res, {
    'payment accepted': (r) => r.status === 201 || r.status === 202,
  });

  paymentAccepted.add(accepted);
  if (res.status === 202) paymentsQueued.add(1);
}
