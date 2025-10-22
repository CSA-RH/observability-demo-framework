import React, { useEffect, useState } from 'react';
import * as ApiHelper from '../ApiHelper';
import { useKeycloak } from "@react-keycloak/web";
import { NavLink, Link, useLocation } from 'react-router-dom';


const ClusterInfo = ({ selectedUserNamespace, setSelectedUserNamespace }) => {

    const location = useLocation();
    const isAdminRoute = location.pathname === "/admin";

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
                console.log("Selecting namespace 0")
                setSelectedUserNamespace(
                    (data.UserNamespaces?.length > 0 ? data.UserNamespaces[0] : null) ?? null);
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

    //TODO: Improve user experience (conditional appearance of all items). 
    if (loading) {
        return <div>Loading...</div>
    }

    if (error) {
        return <div> Error: {error} </div>
    }

    if (!data.Connected) {
        return (<div>Cluster not connected</div>)
    }

    const handleUserNamespaceChange = (e) => {
        const { name, value } = e.target;
        setSelectedUserNamespace(value);
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
                            {isAdmin && !isAdminRoute ? (
                                <select
                                    className="py-1.5 px-3 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 shadow-sm transition duration-150"
                                    id="namespace"
                                    name="user-namespace"
                                    // You should bind the value to a state variable (e.g., selectedNamespace) 
                                    // instead of a static value like "coo" for real usage.
                                    value={selectedUserNamespace} 
                                    onChange={handleUserNamespaceChange}
                                >                                    
                                    {data.UserNamespaces && data.UserNamespaces.map((namespaceName) => (
                                        <option 
                                            key={namespaceName} 
                                            value={namespaceName}
                                        >
                                            {namespaceName}
                                        </option>
                                    ))}
                                </select>
                            ) : (
                                <div>
                                    <strong className="me-2">Namespace:</strong>
                                    <span>{data.Namespace}</span>
                                </div>
                            )}

                        </div>
                    </div>
                </div>
                <div className="col-7 d-flex text-end">
                    <nav className="navbar navbar-expand-lg navbar-dark">
                        <div className="container-fluid">
                            <ul className="navbar-nav">
                                <li className="nav-item"><a className="nav-link" href={data.ConsoleURL}
                                    target="_blank" rel="noopener noreferrer">
                                    Console <i className="fas fa-external-link-alt"></i></a></li>
                                <li className="nav-item"><a className="nav-link" href={data.apiLogsURL}
                                    target="_blank" rel="noopener noreferrer">
                                    Backend Logs <i className="fas fa-external-link-alt"></i></a></li>
                                <li className="nav-item"><a className="nav-link" href={data.JaegerUI}
                                    target="_blank" rel="noopener noreferrer">
                                    Jaeger UI <i className="fas fa-external-link-alt"></i></a></li>
                                <li className="nav-item"><a className="nav-link" href={data.GrafanaURL}
                                    target="_blank" rel="noopener noreferrer">
                                    Grafana <i className="fas fa-external-link-alt"></i></a></li>
                                {isAdmin && (<li className="nav-item"><NavLink to="/simulation"
                                    className={({ isActive }) =>
                                        isActive ? "nav-link active border border-primary bg-primary text-light rounded" : "nav-link"
                                    }>Simulation</NavLink></li>)}
                                {isAdmin && (<li className="nav-item active"><NavLink to="/admin"
                                    className={({ isActive }) =>
                                        isActive ? "nav-link active border border-primary bg-primary text-light rounded" : "nav-link"
                                    }>Administration</NavLink></li>)}
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