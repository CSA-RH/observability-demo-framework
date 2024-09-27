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
        };

        fetchData();        
    }, []);
    
    if (loading) {
        return <div>Loading...</div>
    }

    if (error) {
        return <div> Error: {error} </div>
    }

    if (!data.Connected){
        return (<div>Cluster not connected</div>)
    }
    
    return (
        <div className="key-value-container">            
            <div className="key-value-row">
                <div className="key">Cluster: </div><div className="value">{data.Name}</div>            
            </div>
            <div className="key-value-row">
                <div className="key">Console (Logs): </div><div className="value"><a href={data.ConsoleURL} target="_blank">Link</a><a href={data.apiLogsURL} target="_blank">(Link)</a></div>
            </div>
            <div className="key-value-row">
                <div className="key">Namespace: </div><div className="value">{data.Namespace}</div>
            </div>
            
                <div className="key">API Logs: </div><div className="value"></div>
            
        </div>    
    );
};

export default ClusterInfo;