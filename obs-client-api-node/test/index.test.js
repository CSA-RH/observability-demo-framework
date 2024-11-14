const { getAvailableCook, getAvailableWaiter } = require('../index');

const _agents = new Map();
const _agentsNoWaiters = new Map();
const _agentsNoCooks = new Map();

_agents.set("customer-1", { ip: "1.1.1.1", port: 8080 })
_agents.set("customer-2", { ip: "1.1.1.1", port: 8080 })
_agents.set("waiter-1", { ip: "1.1.1.1", port: 8080 })
_agents.set("waiter-2", { ip: "1.1.1.1", port: 8080 })
_agents.set("waiter-3", { ip: "1.1.1.1", port: 8080 })
_agents.set("cook-1", { ip: "1.1.1.1", port: 8080 })
_agents.set("cook-1", { ip: "1.1.1.1", port: 8080 })

_agentsNoWaiters.set("cook-1", { ip: "1.1.1.1", port: 8080 })
_agentsNoWaiters.set("cook-2", { ip: "1.1.1.1", port: 8080 })

_agentsNoCooks.set("waiter-1", { ip: "1.1.1.1", port: 8080 })
_agentsNoCooks.set("waiter-2", { ip: "1.1.1.1", port: 8080 })
_agentsNoCooks.set("waiter-3", { ip: "1.1.1.1", port: 8080 })
_agentsNoCooks.set("waiter-4", { ip: "1.1.1.1", port: 8080 })

describe('getAvailableWaiter function', () => {
    test('should return an available waiter from a mixed list of cooks, customers and waiters', () => {
        expect(getAvailableWaiter(_agents).name.startsWith("waiter-")).toBe(true);
    });

    test('should return an available waiter from a list of waiters. Validate other fields', () => {        
        expect(getAvailableWaiter(_agentsNoCooks).name.startsWith("waiter-")).toBe(true);
        expect(getAvailableWaiter(_agentsNoCooks).port).toBe(8080);        
        expect(getAvailableWaiter(_agentsNoCooks).ip).toBe("1.1.1.1");
    });

    test('should return an empty object from a list with no waiters', () => {        
        expect(getAvailableWaiter(_agentsNoWaiters)).toBe(null);
    });
});

describe('getAvailableCook function', () => {
    test('should return an available cook from a mixed list of cooks, customers and waiters', () => {
        expect(getAvailableCook(_agents).name.startsWith("cook-")).toBe(true);
    });

    test('should return an available waiter from a list of cooks. Validate other fields', () => {        
        expect(getAvailableCook(_agentsNoWaiters).name.startsWith("cook-")).toBe(true);
        expect(getAvailableCook(_agents).port).toBe(8080);
        expect(getAvailableCook(_agents).ip).toBe("1.1.1.1");
    });

    test('should return an empty object from a list with no waiters', () => {        
        expect(getAvailableCook(_agentsNoCooks)).toBe(null);
    });
});