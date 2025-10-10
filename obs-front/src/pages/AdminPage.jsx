import React, { useState } from 'react';
import { getNamesPool, getRoleMappings } from '../ApiHelper';

const names = getNamesPool();




const AdminPage = () => {

  const [newUser, setNewUser] = useState({ user: "", type: "coo" });
  const [error, setError] = useState("");
  const [formData, setFormData] = useState({
    user: "",
    monitoringType: "coo",
  });

  const handleObservabilityTypeChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
    //setValidationError(""); // Clear validation error on input change
  };

  const handleInputChange = (e) => {
    setNewUser({
      ...newUser,
      [e.target.name]: e.target.value,
    });
  };
  const users = [
    {
      user: "user1",
      type: "user-workload"
    },
    {
      user: "user2",
      type: "coo"
    },
    {
      user: "user3",
      type: "mesh"
    }
  ];

  return (
    <div className="container">
      <div className='row'>
        <div className='col-12 border rounded'>
          <h2 className='mb-0'>Users</h2>
          <div>
            <div className='table-responsive'>
              <table className='table w-100'>
                <thead>
                  <tr>
                    <th>User</th>
                    <th>Observability technology</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((mapping, index) => (
                    <tr key={mapping.user}>

                      <td>
                        <div className="label">{mapping.user}
                        </div>
                      </td>
                      <td>
                        <code>{mapping.type}</code>
                      </td>
                      <td>
                        <button className="btn-circle btn-red"
                          onClick={() => alert("DELETE " + mapping.user)}>
                          <span>&times;</span>
                        </button>
                      </td>
                    </tr>))}
                  <tr key="__addedRow">
                    <td>
                      <input
                        type="text"
                        name="user"
                        value={newUser.user}
                        onChange={handleInputChange}
                        placeholder="User"
                        className="form-control"
                        style={{ width: "120px", textAlign: 'center' }}
                      />
                    </td>
                    <td>
                      <select
                        className="form-select"
                        id="monitoringType"
                        name="monitoringType"
                        value={formData.monitoringType}
                        onChange={handleObservabilityTypeChange}
                      >
                        <option value="user-workload">User Workload</option>
                        <option value="coo">COO</option>
                        <option value="mesh">Mesh</option>
                      </select>

                    </td>
                    <td>
                      <button className="btn-circle btn-green"
                        onClick={() => { alert("CREATE " + newUser.user); setError("Me lo invento"); }}><span>+</span></button>
                    </td>

                  </tr>
                </tbody>
              </table>
            </div>
            {/* Validation Error Message */}
            {error && (
              <div className="alert alert-danger" role="alert">
                {error}
              </div>
            )}
          </div>
        </div>
      </div>
      <div className='row'>
        <div className="col-12 border rounded">
          <h2 className="mb-0">Tecnology mapping</h2>

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