import React, { useEffect, useState } from 'react';
import * as ApiHelper from '../ApiHelper';
import { useKeycloak } from "@react-keycloak/web";
import { Link } from 'react-router-dom';


const ClusterInfo = ({ cluster }) => {

    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const { keycloak, initialized } = useKeycloak();

    const userRoles = keycloak.realmAccess?.roles
    const isAdmin = userRoles?.includes("obs-admin") || false

    useEffect(() => {
        const fetchData = async () => {
            var data = []
            try {
                let headers = new Headers();
                headers.append('Content-Type', 'application/json');
                headers.append('Accept', 'application/json');
                headers.append('Authorization', 'Bearer ' + keycloak.token)

                const response = await fetch(ApiHelper.getInfoUrl(), { headers: headers });
                data = await response.json();
                setData(data);
            } catch (err) {
                setError(err.message);
                console.error('Error fetching data:', error);
            } finally {
                setLoading(false);
            }
            ApiHelper.setGlobalRootConsole(data.ConsoleURL);
            ApiHelper.setglobalCurrentNamespace(data.Namespace);
        };

        fetchData();
    }, [keycloak.token, keycloak.authenticated]);

    if (loading) {
        return <div>Loading...</div>
    }

    if (error) {
        return <div> Error: {error} </div>
    }

    if (!data.Connected) {
        return (<div>Cluster not connected</div>)
    }

    return (
        <div className="container my-3 p-3 border rounded bg-danger text-white">
            <div className='row'>
                <div className="col-3">
                    <div className='row'>
                        <div className="col-12">
                            <strong className="me-2">Cluster:</strong>
                            <span>{data.Name}</span>
                        </div>
                    </div>
                    <div className='row'>
                        <div className="col-12">
                            <strong className="me-2">Namespace:</strong>
                            <span>{data.Namespace}</span>
                        </div>
                    </div>
                </div>
                <div className="col-7 d-flex text-end">
                    <nav class="navbar navbar-expand-lg navbar-dark">
                        <div class="container-fluid">
                            <ul class="navbar-nav">
                                <li class="nav-item"><a class="nav-link" href={data.ConsoleURL}
                                    target="_blank" rel="noopener noreferrer">
                                    Console</a></li>
                                <li class="nav-item"><a class="nav-link" href={data.apiLogsURL}
                                    target="_blank" rel="noopener noreferrer">
                                    Backend Logs</a></li>
                                <li class="nav-item"><a class="nav-link" href={data.JaegerUI}
                                    target="_blank" rel="noopener noreferrer">
                                    Jaeger UI</a></li>
                                <li class="nav-item"><a class="nav-link" href={data.GrafanaURL}
                                    target="_blank" rel="noopener noreferrer">
                                    Grafana</a></li>
                                {isAdmin && (<li class="nav-item"><Link to="/simulation" class="nav-link">Simulation</Link></li>)}
                                {isAdmin && (<li class="nav-item"><Link to="/admin" class="nav-link" href="#">Administration</Link></li> )}
                            </ul>
                        </div>
                    </nav>
                </div>
                <div className='col-2 text-end'>

                    <span>{keycloak?.tokenParsed?.preferred_username}</span>
                    {' '}
                    <a
                        href="#logout"
                        className="text-white text-decoration-underline"
                        onClick={(e) => {
                            e.preventDefault(); // Prevent default link behavior
                            keycloak.logout(); // Trigger Keycloak logout
                        }}
                    >
                        [logout]
                    </a>
                </div>

            </div>


        </div>
    );
};

export default ClusterInfo;