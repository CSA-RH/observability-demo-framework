export const MASTER_API_ADDRESS = import.meta.env.VITE_OBSERVABILITY_DEMO_API


export function getInfoUrl() {
    return `${MASTER_API_ADDRESS}/api/v1/escotilla`
}

export function getSimulationUrl(userId) {
    return `${MASTER_API_ADDRESS}/api/v1/users/${userId}/simulation`
}

export function getKickUrl(userId, agentId) {
    return `${MASTER_API_ADDRESS}/api/v1/users/${userId}/simulation/kick/${agentId}`
}

export function getAgentsMetricsUrl(userId) {
    return `${MASTER_API_ADDRESS}/api/v1/users/${userId}/simulation/metrics`
}

export function getClusterAlertDefinitionUrl(userId, alertId) {
    return `${MASTER_API_ADDRESS}/api/v1/users/${userId}/simulation/alerts` + (alertId ? "/" + alertId: "")
}

export function getUserListUrl() {
    return `${MASTER_API_ADDRESS}/api/v1/users`
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

export function isValidK8sName(name) {
    const DNS_SUBDOMAIN_NAME_REGEX = /^[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*$/;
    const MAX_LENGTH = 253; // Maximum length for DNS Subdomain Names

    if (!name || name.length > MAX_LENGTH) {
        return false;
    }

    return DNS_SUBDOMAIN_NAME_REGEX.test(name);
}

// src/utils/PasswordGeneratorUtil.js

/**
 * Generates a cryptographically secure random password.
 * @param {number} length - The desired password length.
 * @param {Object} options - Character set options.
 * @param {boolean} [options.upper=true] - Include uppercase letters.
 * @param {boolean} [options.lower=true] - Include lowercase letters.
 * @param {boolean} [options.numbers=true] - Include numbers.
 * @param {boolean} [options.symbols=false] - Include special symbols.
 * @returns {string} The generated password.
 */
export function generateRandomPassword(length = 16, options = {}) {
  const {
    upper = true,
    lower = true,
    numbers = true,
    symbols = false,
  } = options;

  const lowerChars = 'abcdefghijklmnopqrstuvwxyz';
  const upperChars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
  const numberChars = '0123456789';
  const symbolChars = '!@#$%^&*()_+=-[]{}|;:,.<>?';

  let allChars = '';
  const requiredChars = [];

  // 1. Build the character pool and ensure at least one of each selected type is included
  if (lower) {
    allChars += lowerChars;
    requiredChars.push(lowerChars[Math.floor(Math.random() * lowerChars.length)]);
  }
  if (upper) {
    allChars += upperChars;
    requiredChars.push(upperChars[Math.floor(Math.random() * upperChars.length)]);
  }
  if (numbers) {
    allChars += numberChars;
    requiredChars.push(numberChars[Math.floor(Math.random() * numberChars.length)]);
  }
  if (symbols) {
    allChars += symbolChars;
    requiredChars.push(symbolChars[Math.floor(Math.random() * symbolChars.length)]);
  }

  // Handle case where no options are selected
  if (allChars.length === 0) {
    return ''; 
  }

  // 2. Fill the remaining length randomly from the full character pool
  const remainingLength = length - requiredChars.length;
  let randomChars = '';

  // Use crypto API for secure randomness
  const randomArray = new Uint32Array(remainingLength);
  window.crypto.getRandomValues(randomArray);

  for (let i = 0; i < remainingLength; i++) {
    const randomIndex = randomArray[i] % allChars.length;
    randomChars += allChars[randomIndex];
  }

  // 3. Combine required and random characters
  let passwordArray = [...requiredChars, ...randomChars.split('')];

  // 4. Securely shuffle the password array to prevent predictable patterns
  for (let i = passwordArray.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [passwordArray[i], passwordArray[j]] = [passwordArray[j], passwordArray[i]];
  }

  return passwordArray.join('');
}