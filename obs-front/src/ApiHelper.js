export const MASTER_API_ADDRESS = import.meta.env.VITE_OBSERVABILITY_DEMO_API


export function getInfoUrl() {
    return `${MASTER_API_ADDRESS}/info`
}

export function getSimulationUrl() {
    return `${MASTER_API_ADDRESS}/simulation`
}

export function getKickUrl(agentIp) {
    return `${MASTER_API_ADDRESS}/kick`
}

export function getAgentsMetricsUrl() {
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

export function getAlertRulesAddress() {
    return globalRootConsole + "/monitoring/alertrules?rowFilter-alerting-rule-source=user"
}

export function getObserveLinkForMetric(metric, job) {
    return `${globalRootConsole}/monitoring/query-browser?query0=${metric}%7Bjob%3D"${job}"%7D`
}

export function getRoleMappings() {
    return [
        {
            role: "customer",
            image: "obs-client-node:latest",
            drawing: "logo-customer.svg"
        },
        {
            role: "waiter",
            image: "obs-client-dotnet:latest",
            drawing: "logo-waiter.svg"
        },
        {
            role: "cook",
            image: "obs-client-node:latest",
            drawing: "logo-cook.svg"
        }
    ];
}

export function getNamesPool() {
    return [
        "duda",
        "sandro",
        "isco",
        "santa-cruz",
        "salva",
        "roteta",
        "koke",
        "weligton",
        "cazorla",
        "nacho",
        "fornals",
        "van-nistelrooy",
        "musampa",
        "rufete",
        "apono",
        "rosales",
        "valcarce",
        "gamez",
        "maresca",
        "baptista",
        "amrabat",
        "charles",
        "joaquin",
        "samuel-garcia",
        "eliseu",
        "kameni",
        "camacho",
        "willy-caballero",
        "migueli",
        "antonio-hidalgo",
        "pepillo",
        "basti",
        "josemi",
        "monreal",
        "quino",
        "juanmi",
        "nacho-perez",            
        "manolo-reina",
        "pellicer",
        "jaro",
        "makanaky",
        "toulalan",
        "antonio-benitez",
        "adrian",
        "dario-silva",
        "movilla",
        "antonito", 
        "fleitas", 
        "guerini",
        "castronovo",
        "usuriaga",
        "paquito",
        "alvarez",
        "bernardi",
        "americo",
        "montero",
        "arias",
        "arles",
        "aido",
        "viberti",
        "vilanova",
        "varela",
        "rodriguez",
        "cantaruti",
        "cabral",
        "roldan",
        "canabal",
        "bazan",
        "deusto",
        "goroechea",
        "peribaldo",
        "pineda",
        "husillos",
        "jantunen",
        "bonacic",
        "lauridsen",
        "pons",
        "martinez",
        "borreda",
        "munoz-perez",
        "soriano", 
        "contreras",
        "elder", 
        "goitia",
        "conejo"
    ];
}