export const MASTER_API_ADDRESS = 'https://obs-main-api-observability-demo.apps.am1f75h1xc1037e792.germanywestcentral.aroapp.io'

export function getInfoUrl()  {
    return `${MASTER_API_ADDRESS}/info`
}

export function getAgentsStatus(){
    return `${MASTER_API_ADDRESS}/obs-agents`
}

export function getSimulationUrl(){
    return `${MASTER_API_ADDRESS}/simulation`
}

export function getKickUrl(agentIp){
    return `${MASTER_API_ADDRESS}/kick`
}

