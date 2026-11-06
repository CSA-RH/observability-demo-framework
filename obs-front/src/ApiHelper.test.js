import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
    MASTER_API_ADDRESS,
    generateRandomPassword,
    getClusterAlertDefinitionUrl,
    getKickUrl,
    getObserveLinkForMetric,
    getOperationStatusLabel,
    getOperationUrl,
    getPodAddress,
    getPrometheusRoute,
    getSimulationUrl,
    getUsernameValidationError,
    isValidK8sName,
    isValidUsername,
    pollOperation,
    setGlobalRootConsole,
    setglobalCurrentNamespace,
} from './ApiHelper';

const API = 'https://obs-main-api.apps.example.com';

describe('API URLs', () => {
    it('are built from VITE_OBSERVABILITY_DEMO_API', () => {
        expect(MASTER_API_ADDRESS).toBe(API);
        expect(getSimulationUrl('abc')).toBe(`${API}/api/v1/users/abc/simulation`);
        expect(getKickUrl('abc', 'cook-1')).toBe(`${API}/api/v1/users/abc/simulation/kick/cook-1`);
        expect(getOperationUrl('op-1')).toBe(`${API}/api/v1/operations/op-1`);
    });

    it('alert URL optionally includes the alert id', () => {
        expect(getClusterAlertDefinitionUrl('abc')).toBe(`${API}/api/v1/users/abc/simulation/alerts`);
        expect(getClusterAlertDefinitionUrl('abc', 'a1')).toBe(`${API}/api/v1/users/abc/simulation/alerts/a1`);
    });
});

describe('console links', () => {
    beforeEach(() => {
        setGlobalRootConsole('https://console.example.com');
        setglobalCurrentNamespace('obs-demo');
    });

    it('builds pod address in the user namespace', () => {
        expect(getPodAddress('pod-1', 'abc')).toBe('https://console.example.com/k8s/ns/obs-demo-abc/pods/pod-1');
    });

    it('builds metric links per monitoring stack', () => {
        expect(getObserveLinkForMetric('orders', 'cook', { monitoringType: 'user-workload' })).toBe(
            'https://console.example.com/monitoring/query-browser?query0=orders%7Bjob%3D"cook"%7D',
        );
        expect(getObserveLinkForMetric('orders', 'cook', { monitoringType: 'coo', username: 'abc' })).toBe(
            'https://prometheus-abc-obs-demo-abc.apps.example.com/query?g0.expr=orders%7Bjob%3D"cook"%7D&g0.tab=graph',
        );
        expect(getObserveLinkForMetric('orders', 'cook', { monitoringType: 'other' })).toBe('#');
    });

    it('derives the Prometheus route from the API cluster suffix', () => {
        expect(getPrometheusRoute('abc')).toBe('https://prometheus-abc-obs-demo-abc.apps.example.com');
    });
});

describe('username validation (mirrors backend validators.py)', () => {
    it.each(['abc', 'user-1', 'x'.repeat(63)])('accepts %s', (name) => {
        expect(isValidUsername(name)).toBe(true);
        expect(getUsernameValidationError(name)).toBeNull();
    });

    it.each([
        ['', 'cannot be empty'],
        ['ab', 'at least 3'],
        ['x'.repeat(64), 'at most 63'],
        ['Upper', 'valid DNS label'],
        ['-abc', 'valid DNS label'],
    ])('rejects "%s"', (name, fragment) => {
        expect(isValidUsername(name)).toBe(false);
        expect(getUsernameValidationError(name)).toContain(fragment);
    });

    // Known gap: the backend rejects reserved names, the UI only finds out after submitting.
    it.fails('rejects reserved usernames like the backend', () => {
        expect(isValidUsername('admin')).toBe(false);
    });

    it('validates k8s DNS subdomain names', () => {
        expect(isValidK8sName('a.b-c.d')).toBe(true);
        expect(isValidK8sName('A.b')).toBe(false);
        expect(isValidK8sName('a'.repeat(254))).toBe(false);
    });
});

describe('generateRandomPassword', () => {
    it('honours length and includes every selected character class', () => {
        for (let i = 0; i < 20; i++) {
            const password = generateRandomPassword(16, { symbols: true });
            expect(password).toHaveLength(16);
            expect(password).toMatch(/[a-z]/);
            expect(password).toMatch(/[A-Z]/);
            expect(password).toMatch(/[0-9]/);
            expect(password).toMatch(/[^a-zA-Z0-9]/);
        }
    });

    it('restricts to the selected classes', () => {
        expect(generateRandomPassword(32, { upper: false, lower: false })).toMatch(/^[0-9]{32}$/);
        expect(generateRandomPassword(8, { upper: false, lower: false, numbers: false })).toBe('');
    });
});

describe('pollOperation', () => {
    const jsonResponse = (body, status = 200) => ({ ok: status < 400, status, json: async () => body });

    beforeEach(() => {
        vi.useFakeTimers();
    });
    afterEach(() => {
        vi.useRealTimers();
        vi.unstubAllGlobals();
    });

    it('polls until the operation succeeds, reporting progress', async () => {
        const fetchMock = vi.fn()
            .mockResolvedValueOnce(jsonResponse({ status: 'pending' }))
            .mockResolvedValueOnce(jsonResponse({ status: 'running' }))
            .mockResolvedValueOnce(jsonResponse({ status: 'succeeded', result: 42 }));
        vi.stubGlobal('fetch', fetchMock);
        const onProgress = vi.fn();

        const promise = pollOperation('op-1', 'tok', { intervalMs: 10, onProgress });
        await vi.runAllTimersAsync();

        await expect(promise).resolves.toEqual({ status: 'succeeded', result: 42 });
        expect(fetchMock).toHaveBeenCalledTimes(3);
        expect(onProgress.mock.calls.map(([op]) => op.status)).toEqual(['pending', 'running', 'succeeded']);
        expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe('Bearer tok');
    });

    it('refreshes the Keycloak token before each request', async () => {
        vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ status: 'succeeded' })));
        const keycloak = { token: 'fresh', updateToken: vi.fn().mockResolvedValue(true) };

        await pollOperation('op-1', keycloak);

        expect(keycloak.updateToken).toHaveBeenCalledWith(30);
        expect(fetch.mock.calls[0][1].headers.Authorization).toBe('Bearer fresh');
    });

    it.each([
        [jsonResponse({ status: 'failed', error: 'quota exceeded' }), 'quota exceeded'],
        [jsonResponse({ status: 'failed' }), 'Operation failed'],
        [jsonResponse({}, 404), 'Operation not found'],
        [jsonResponse({}, 500), 'Failed to fetch operation status (500)'],
    ])('rejects on failure (%#)', async (response, message) => {
        vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response));
        await expect(pollOperation('op-1', 'tok')).rejects.toThrow(message);
    });

    it('times out', async () => {
        vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ status: 'running' })));
        const promise = pollOperation('op-1', 'tok', { intervalMs: 100, timeoutMs: 250 });
        const assertion = expect(promise).rejects.toThrow('Operation timed out');
        await vi.runAllTimersAsync();
        await assertion;
    });
});
