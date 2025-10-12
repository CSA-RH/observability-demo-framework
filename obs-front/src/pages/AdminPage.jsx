import React, { useState } from 'react';
import { getNamesPool, getRoleMappings, isValidK8sName, generateRandomPassword } from '../ApiHelper';
import ConfirmationModal from '../components/ConfirmationModal';
import PasswordCell from '../components/PasswordCell';

const names = getNamesPool();

const AdminPage = () => {
  const [showModal, setShowModal] = useState(false);
  const [modalType, setModalType] = useState(null) // 'create' or 'delete'
  const [userToProcess, setUserToProcess] = useState(null);

  const [error, setError] = useState("");
  const [users, setUsers] = useState([
    {
      user: "user1",
      monitoringType: "user-workload",
      password: "MeLoInvento1"

    },
    {
      user: "user2",
      monitoringType: "coo",
      password: "MeLoInvento2"
    },
    {
      user: "user3",
      monitoringType: "mesh",
      password: "MeLoInvento3"
    }
  ]);
  const [userData, setUserData] = useState({
    user: "",
    monitoringType: "coo",
  });

  // --- Functions to Trigger Modals ---

  const handleShowCreateModal = () => {
    setModalType('create');
    setUserToProcess(userData);
    setShowModal(true);
  };

  const handleShowDeleteModal = (user) => {
    setModalType('delete');
    setUserToProcess(user);
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setModalType(null);
    setUserToProcess(null);
  };

  const handleConfirmAction = () => {
    if (modalType === 'create') {
      console.log(`CONFIRMED: Creating user ${userData.user}...`);
      // API call to create user goes here
      userData.password = generateRandomPassword();
      users.push(userData);
      setUsers(users);
      setUserData({
        user: "",
        monitoringType: "coo"
      });
    } else if (modalType === 'delete') {
      console.log(`CONFIRMED: Deleting user ID ${userToProcess}...`);
      // API call to delete user goes here
      const updatedUsers = users.filter(userObj => userObj.user !== userToProcess);
      setUsers(updatedUsers);
    }
    // Close the modal after the action
    handleCloseModal();
    setError("");
  };

  const getModalProps = () => {
    switch (modalType) {
      case 'create':
        return {
          title: "Confirm User Creation",
          body: `Are you sure you want to create a new user named "${userData.user}"?`,
          confirmText: "Create User",
          // Bootstrap class for success (green)
          confirmClass: "btn-success"
        };
      case 'delete':
        return {
          title: "Confirm User Deletion",
          body: `WARNING: This action cannot be undone. Do you want to permanently delete user "${userToProcess}"?`,
          confirmText: "Delete User",
          // Bootstrap class for danger (red)
          confirmClass: "btn-danger"
        };
      default:
        return {};
    }
  };

  const modalProps = getModalProps();

  const handleInputChange = (e) => {
    setUserData({
      ...userData,
      [e.target.name]: e.target.value,
    });
    setError("");
  };

  const isUserUnique = (user) => {
    return !users.some(userObj => user === userObj.user);
  }

  const handleAddNewUser = (e) => {
    // Validation
    if (!isValidK8sName(userData.user)) {      
      setError("Name not valid");
      return;
    }
    if (!isUserUnique(userData.user)){
      setError(`user ${userData.user} already exists`);
      return;
    }
    // Show Modal Window
    handleShowCreateModal();
  }

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
                    <th >Observability technology</th>
                    <th className="w-25">Password</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((mapping, index) => (
                    <tr key={index}>

                      <td>
                        <div className="label">{mapping.user}
                        </div>
                      </td>
                      <td>
                        <code>{mapping.monitoringType}</code>
                      </td>
                      <td>
                        <PasswordCell password={mapping.password} /> 
                      </td>
                      <td>
                        <button className="btn-circle btn-red"
                          onClick={() => handleShowDeleteModal(mapping.user)}>
                          <span>&times;</span>
                        </button>
                      </td>
                    </tr>))}
                  <tr key="__addedRow">
                    <td>
                      <input
                        type="text"
                        name="user"
                        value={userData.user}
                        onChange={handleInputChange}
                        placeholder="User"
                        className="form-control"
                        style={{ width: "180px", textAlign: 'center' }}
                      />
                    </td>
                    <td>
                      <select
                        className="form-select"
                        id="monitoringType"
                        name="monitoringType"
                        value={userData.monitoringType}
                        onChange={handleInputChange}                        
                      >
                        <option value="user-workload">User Workload</option>
                        <option value="coo">COO</option>
                        <option value="mesh">Mesh</option>
                      </select>
                    </td>
                    <td>                      
                    </td>
                    <td>
                      <button className="btn-circle btn-green"
                        onClick={handleAddNewUser}><span>+</span></button>
                    </td>

                  </tr>
                </tbody>
              </table>
              <ConfirmationModal
                show={showModal}
                onHide={handleCloseModal}
                onConfirm={handleConfirmAction}
                {...modalProps} // Pass the dynamic props for the current use case
              />
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