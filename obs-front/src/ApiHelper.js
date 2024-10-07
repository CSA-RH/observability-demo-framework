//export const MASTER_API_ADDRESS = 'https://obs-main-api-observability-demo.apps.zm1iwcvbvd702c1f99.germanywestcentral.aroapp.io'
//export const MASTER_API_ADDRESS = 'https://obs-main-api-obs-test.apps.csaclassic2.9gcg.p1.openshiftapps.com'
export const MASTER_API_ADDRESS = 'http://localhost:8000'

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