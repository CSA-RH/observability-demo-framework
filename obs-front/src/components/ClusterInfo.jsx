import React, { useEffect, useState, useCallback } from 'react';
import * as ApiHelper from '../ApiHelper';
import { useKeycloak } from "@react-keycloak/web";
import { NavLink, Link, useLocation } from 'react-router-dom';
import { notifyError } from '../services/NotificationService';
import { eventBus, USERS_UPDATED_EVENT } from '../services/EventBus';

const ClusterInfo = ({ selectedUser, setSelectedUser }) => {

    const location = useLocation();
    const isAdminRoute = location.pathname === "/admin";

    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const { keycloak, initialized } = useKeycloak();
    const userRoles = keycloak.realmAccess?.roles
    const isAdmin = userRoles?.includes("obs-admin") || false

    const fetchData = useCallback(async () => {
        var data = []
        try {
            let headers = new Headers();
            headers.append('Content-Type', 'application/json');
            headers.append('Accept', 'application/json');
            headers.append('Authorization', 'Bearer ' + keycloak.token);

            const response = await fetch(ApiHelper.getInfoUrl(), { headers: headers });
            data = await response.json();
            if (response.status == 200) {
                setData(data);
                // Check if the currently selected user still exists in the new list.
                const userExists = data.Users?.find(u => u.username === selectedUser?.username);

                // If they don't (or if no user was selected), default to the first user.
                if (!userExists) {
                    setSelectedUser(
                        (data.Users?.length > 0 ? data.Users[0] : null) ?? null);
                }
                // If they *do* exist, the 'selectedUser' state remains unchanged, 
                // preventing the dropdown from unexpectedly resetting.
            }
            else {
                setError(`Error fetching data[${response.status}]`);
                notifyError("Error fetching cluster data. " + data);
            }
        } catch (err) {
            setError(err.message);
            notifyError('Error fetching data:', err);
        } finally {
            setLoading(false);
        }
        ApiHelper.setGlobalRootConsole(data.ConsoleURL);
        ApiHelper.setglobalCurrentNamespace(data.Namespace);
    }, [keycloak.token, keycloak.authenticated, setSelectedUser, selectedUser?.username]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    useEffect(() => {
        // Define the handler function
        const handleUsersUpdated = () => {
            console.log('User list updated, refetching cluster info...');
            fetchData();
        };

        // Add the listener
        eventBus.addEventListener(USERS_UPDATED_EVENT, handleUsersUpdated);

        // Return a cleanup function to remove the listener
        return () => {
            eventBus.removeEventListener(USERS_UPDATED_EVENT, handleUsersUpdated);
        };
    }, [fetchData]);

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

    const findUserByUsername = (targetUsername, userList) => {
        const selectedUser = userList.find(user => user.username === targetUsername);
        return selectedUser;
    }

    const handleUserNamespaceChange = (e) => {
        const { name, value } = e.target;
        setSelectedUser(findUserByUsername(value, data.Users));
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
                                // Add this check:
                                (data.Users && data.Users.length > 0) ? (
                                    <select
                                        className="py-1.5 px-3 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 shadow-sm transition duration-150"
                                        id="namespace"
                                        name="user-namespace"
                                        value={selectedUser?.username}
                                        onChange={handleUserNamespaceChange}
                                    >
                                        {/* The check in the line above guarantees data.Users is a non-empty array here */}
                                        {data.Users.map((user) => (
                                            <option
                                                key={user.username}
                                                value={user.username}
                                            >
                                                {user.username}
                                            </option>
                                        ))}
                                    </select>
                                ) : (
                                    // OPTIONAL: Show a message if no users exist
                                    <div className="py-1.5 px-3 text-sm text-gray-500">
                                        No users available.
                                    </div>
                                )
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
                                <li className="nav-item">
                                    <a className="nav-link" href={data.ConsoleURL}
                                        target="_blank" rel="noopener noreferrer">
                                        <img src="/openshift.svg" className="nav-icon-svg" style={{ backgroundColor: "white", height: "40px", width: "auto", verticalAlign: "middle" }}
                                            alt="OpenShift" />
                                    </a>
                                </li>
                                <li className="nav-item">
                                    <a className="nav-link" href={data.apiLogsURL}
                                        target="_blank" rel="noopener noreferrer">
                                        <img src="/logging.svg" className="nav-icon-svg" style={{ height: "40px", width: "auto", verticalAlign: "middle" }}
                                            alt="Logging" />
                                    </a>
                                </li>
                                <li className="nav-item">
                                    <a className="nav-link" href={data.JaegerUI}
                                        target="_blank" rel="noopener noreferrer" title="JaegerUI">
                                        <img src="/jaeger.svg" className="nav-icon-svg" style={{ backgroundColor: "white", height: "40px", width: "auto", verticalAlign: "middle" }}
                                            alt="Jaeger UI" />
                                    </a>
                                </li>
                                <li className="nav-item">
                                    <a className="nav-link" href={data.GrafanaURL}
                                        target="_blank" rel="noopener noreferrer" title="Grafana">
                                        <img src="/grafana.svg" className="nav-icon-svg" style={{ height: "40px", width: "auto", verticalAlign: "middle" }}
                                            alt="Grafana" />
                                    </a>
                                </li>
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