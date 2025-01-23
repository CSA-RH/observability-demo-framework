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
    return `${MASTER_API_ADDRESS}/alerts`
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

export function getAlertRulesAddress(){
    return globalRootConsole + "/monitoring/alertrules?rowFilter-alerting-rule-source=user"    
}

export function getObserveLinkForMetric(metric, job){
    return `${globalRootConsole}/monitoring/query-browser?query0=${metric}%7Bjob%3D"${job}"%7D`
}