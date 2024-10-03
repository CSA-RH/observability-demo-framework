import React, { useEffect, useState } from 'react';
import * as ApiHelper from '../ApiHelper'

const ClusterInfo = ({ cluster }) => {

    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchData = async () => {
            var data = []
            try {
                let headers = new Headers();
                headers.append('Content-Type', 'application/json');
                headers.append('Accept', 'application/json');
                headers.append('Origin', 'http://localhost:3000');

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
    }, []);

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
        <div className="key-value-container">            
            <div className="banner">
                <div className="banner-info">
                    <div className="cluster-info">
                        <span className="info-title">Cluster:</span>
                        <span className="info-value">{data.Name}</span>
                    </div>
                    <div className="namespace-info">
                        <span className="info-title">Namespace:</span>
                        <span className="info-value">{data.Namespace}</span>
                    </div>
                </div>

                {/* -- Links Section --> */}
                <div className="banner-links">
                    <a href={data.ConsoleURL} className="link" target="_blank" rel="noopener noreferrer">Console</a> 
                    <a href={data.apiLogsURL} className="link" target="_blank" rel="noopener noreferrer">API</a>
                    <a href={data.JaegerUI} className="link" target="_blank" rel="noopener noreferrer">Jaeger</a>
                </div>

                {/*-- Toggle Buttons Section -- */}
                <div className="banner-toggles">
                    <label className="switch">
                        <input type="checkbox" defaultChecked />
                            <span className="slider"></span>
                    </label>
                    <span className="toggle-label">Auto-instrumentation</span>

                    {/* <label className="switch">
                        <input type="checkbox" />
                            <span className="slider"></span>
                    </label>
                    <span className="toggle-label">Feature 2</span>*/}
                </div>
            </div>


        </div>
    );
};

export default ClusterInfo;