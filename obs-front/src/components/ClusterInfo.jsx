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
                headers.append('Origin', 'http://localhost:3000');  //TODO: Review

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
        <div className="container my-3 p-3 border rounded bg-danger text-white">
            <div className='row'>
                <div className="col-6">
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
                <div className="col-6 text-end">
                    <a href={data.ConsoleURL} className="btn btn-primary me-2 mb-2" target="_blank" rel="noopener noreferrer">Console</a>
                    <a href={data.apiLogsURL} className="btn btn-primary me-2 mb-2" target="_blank" rel="noopener noreferrer">API</a>
                    <a href={data.JaegerUI} className="btn btn-primary me-2 mb-2" target="_blank" rel="noopener noreferrer">Jaeger</a>
                </div>
            </div>


        </div>
    );
};

export default ClusterInfo;