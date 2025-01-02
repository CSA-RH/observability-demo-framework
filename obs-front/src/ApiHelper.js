export const MASTER_API_ADDRESS = process.env.REACT_APP_OBSERVABILITY_DEMO_API


export function getInfoUrl()  {
    return `${MASTER_API_ADDRESS}/info`
}

export function getSimulationUrl(){
    return `${MASTER_API_ADDRESS}/simulation`
}

export function getKickUrl(agentIp){
    return `${MASTER_API_ADDRESS}/kick`
}

export function getAgentsMetricsUrl(){
    return `${MASTER_API_ADDRESS}/metrics`
}

export function getClusterAlertDefinitionUrl() {
    return `${MASTER_API_ADDRESS}/alert`
}

//Root console address
export let globalRootConsole = 'N/A';

export const setGlobalRootConsole = (newValue) => {
    globalRootConsole = newValue;
};

//Current namespace
export let globalCurrentNamespace = "N/A"

export const setglobalCurrentNamespace = (newValue) => {
    globalCurrentNamespace = newValue;
};

export function getPodAddress(podName) {
    return globalRootConsole + '/k8s/ns/' + globalCurrentNamespace + '/pods/' + podName;
}

export function getPodLogsAddress(podName) {
    return getPodAddress(podName) + "/logs"
}