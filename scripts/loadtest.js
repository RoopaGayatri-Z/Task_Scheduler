
import http from 'k6/http';
import { check } from 'k6';

export const options = {
    scenarios: {
        task_load_test: {
            executor: 'shared-iterations',
            vus: 50,
            iterations: 5000,
            maxDuration: '10m',
        },
    },
};

export default function () {
    const token = __ENV.K6_TOKEN;

    const response = http.get(
        'http://localhost:8080/tasks',
        {
            headers: {
                Authorization: `Bearer ${token}`,
            },
        }
    );

    check(response, {
        'status is 200': (r) => r.status === 200,
    });
}
