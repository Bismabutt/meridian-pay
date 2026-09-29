// Rollback drill.
//
// Discovery established that a bad release took three hours to recover
// because there was no rollback procedure and the person who knew the
// recovery steps was on leave.
//
// This scenario holds steady load while a deliberately broken version is
// deployed and then rolled back. The measurement is time to recovery and
// how many customers were affected.

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
const paymentSuccess = new Rate('payment_success_rate');
const errorsObserved = new Counter('errors_observed');

export const options = {
  scenarios: {
    steady: {
      executor: 'constant-arrival-rate',
      rate: 80,
      timeUnit: '1s',
      duration: '10m',
      preAllocatedVUs: 50,
      maxVUs: 200,
      exec: 'submitPayment',
    },
  },

  // No thresholds. This run is expected to fail during the bad deploy;
  // the value is in measuring how long the failure lasts, not in passing.
};

export function setup() {
  const business = pickBusiness();
  const token = login(business);
  if (!token) throw new Error('setup failed: could not authenticate');

  console.log('');
  console.log('  Drill timeline');
  console.log('  0:00 to 3:00   steady state, healthy version');
  console.log('  3:00           deploy the broken image:');
  console.log('                 kubectl set image deployment/payment-service \\');
  console.log('                   payment-service=meridian-pay/payment-service:broken \\');
  console.log('                   -n meridian-money');
  console.log('  3:00 to 5:00   error rate climbs, note the time it starts');
  console.log('  5:00           roll back, and start a timer:');
  console.log('                 kubectl rollout undo deployment/payment-service -n meridian-money');
  console.log('  5:00 onward    stop the timer when the error rate returns to zero');
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

  const ok = check(res, {
    'payment accepted': (r) => r.status === 201 || r.status === 202,
  });

  paymentSuccess.add(ok);
  if (!ok) errorsObserved.add(1);
}
