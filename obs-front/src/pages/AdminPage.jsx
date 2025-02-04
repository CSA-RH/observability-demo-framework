import React from 'react';
import { getNamesPool, getRoleMappings } from '../ApiHelper';

const names = getNamesPool();

const AdminPage = () => {
  return (
    <div className="container">
      <div className='row'>
        <div className="col-12 border rounded">
          <h2 className="∫mb-0">Tecnology mapping</h2>
          <div>
            <div className='table-responsive'>
              <table className='table w-100'>
                <thead>
                  <tr>
                    <th>Drawing</th>
                    <th>Role</th>
                    <th>Container Image</th>
                  </tr>
                </thead>
                <tbody>
                  {getRoleMappings().map((mapping, index) => (
                    <tr key={mapping.role}>
                      <td>
                      <img
                        src={mapping.drawing}
                        alt={`Button ${index + 1}`}
                        style={{ width: '75px', height: '25px', objectFit: 'contain' }}
                    />
                      </td>
                      <td>
                        <div className="label">{mapping.role}
                        </div>
                      </td>
                      <td>
                        <code>{mapping.image}</code>
                      </td>                      
                    </tr>))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
      <div className='row mt-4'>
        <div className="col-12 border rounded">
          <h2 className="mb-0">Pool of names</h2>          
            {getNamesPool().map((item) => (<div key={item} className="mb-1 label label-container">{item}</div>))}          
        </div>
      </div>
    </div>
  );
};

export default AdminPage;