export const MASTER_API_ADDRESS = 'https://obs-main-api-observability-demo.apps.zm1iwcvbvd702c1f99.germanywestcentral.aroapp.io'

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