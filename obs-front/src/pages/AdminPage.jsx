import React, { useState, useEffect } from 'react';
import { getNamesPool, getRoleMappings, isValidK8sName, generateRandomPassword, getUserListUrl } from '../ApiHelper';
import ConfirmationModal from '../components/ConfirmationModal';
import PasswordCell from '../components/PasswordCell';
import { useKeycloak } from "@react-keycloak/web";


const names = getNamesPool();

const AdminPage = () => {
  const [showModal, setShowModal] = useState(false);
  const [modalType, setModalType] = useState(null) // 'create' or 'delete'
  const [userToProcess, setUserToProcess] = useState(null);

  const [error, setError] = useState("");
  const [users, setUsers] = useState([]);
  const { keycloak, initialized } = useKeycloak();
  const [newUserData, setNewUserData] = useState({
    username: "",
    monitoringType: "coo",
  });

  // --- Manage users --- 

  useEffect(() => {
    const fetchUsers = async () => {
      setError("");
      try {        
        const userListResponse = await fetch(getUserListUrl(), {
          method: "GET",
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${keycloak.token}` 
         }});
        if (userListResponse.status > 299) {
          setUsers([]);
          setError(`Error fetching users[${userListResponse.status}]`)
        }
        else {
          const users_json = await userListResponse.json();
          setUsers(users_json);
        }
      } catch(error) {        
        const errorMessage = `Error fetching users[${error}]`
        console.error(errorMessage);
        setError(errorMessage);
      }
    };
  
    fetchUsers();
  
    }, [keycloak.token, keycloak.authenticated]); // Empty dependency array to run once on component mount

  // --- Functions to manage users ---
  const deleteUser = async (user) => {    
    setError("");
    try {      
      const deleteUserResponse = await fetch(getUserListUrl(), {
        method: "DELETE",
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${keycloak.token}` 
        }, 
        body: JSON.stringify({
          'username': user
        })
      
      });
      if (deleteUserResponse.status > 299) {
        setUsers([]);
        setError(`Error deleting user ${user}[${deleteUserResponse.status}]`)
      }      
    } catch(error) {        
      const errorMessage = `Error fetching users[${error}]`
      console.error(errorMessage);
      setError(errorMessage);
    }
  };

  const postUser = async (user) => {
    setError("");
    try {      
      const postUserResponse = await fetch(getUserListUrl(), {
        method: "POST",
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${keycloak.token}` 
        }, 
        body: JSON.stringify(user)      
      });
      if (postUserResponse.status > 299) {
        setUsers([]);
        setError(`Error creating user ${user.username}[${deleteUserResponse.status}]`)
      }      
    } catch(error) {        
      const errorMessage = `Error creating user[${error}]`
      console.error(errorMessage);
      setError(errorMessage);
    }
  };

  // --- Functions to Trigger Modals ---

  const handleShowCreateModal = () => {
    setModalType('create');
    setUserToProcess(newUserData);
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

  const handleConfirmAction = async () => {
    if (modalType === 'create') {
      console.log(`CONFIRMED: Creating user ${newUserData.username}...`);
      // API call to create user goes here

      newUserData.password = generateRandomPassword();
      users.push(newUserData);
      setUsers(users);
      setNewUserData({
        username: "",
        monitoringType: "coo"
      });
      //PUSH USER
      await postUser(newUserData);
    } else if (modalType === 'delete') {
      console.log(`CONFIRMED: Deleting user ID ${userToProcess}...`);
      // API call to delete user 
      await deleteUser(userToProcess);
      const updatedUsers = users.filter(userObj => userObj.username !== userToProcess);
      setUsers(updatedUsers);
    }
    // Close the modal after the action
    handleCloseModal();
    setError("");
    setNewUserData({username: "", monitoringType: "coo"})
  };

  const getModalProps = () => {
    switch (modalType) {
      case 'create':
        return {
          title: "Confirm User Creation",
          body: `Are you sure you want to create a new user named "${newUserData.username}"?`,
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
    setNewUserData({
      ...newUserData,
      [e.target.name]: e.target.value,
    });
    setError("");
  };

  const isUserUnique = (user) => {
    return !users.some(userObj => user === userObj.username);
  }

  const isReservedName = (user) => {
    return ["admin", "cluster-admin"].includes(user);
  }

  const handleAddNewUser = (e) => {
    // Validation
    if (!isValidK8sName(newUserData.username)) {      
      setError("Name not valid.");
      return;
    }
    if (!isReservedName(newUserData.username)) {
      setError(`Username ${newUserData.username} is reserved.`);
    }
    if (!isUserUnique(newUserData.username)){
      setError(`user ${newUserData.username} already exists.`);
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
                        <div className="label">{mapping.username}
                        </div>
                      </td>
                      <td>
                        <code>{mapping.monitoringType}</code>
                      </td>                      
                      <PasswordCell password={mapping.password} />
                      <td>
                        <button className="btn-circle btn-red"
                          onClick={() => handleShowDeleteModal(mapping.username)}>
                          <span>&times;</span>
                        </button>
                      </td>
                    </tr>))}
                  <tr key="__addedRow">
                    <td>
                      <input
                        type="text"
                        name="username"
                        value={newUserData.username}
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
                        value={newUserData.monitoringType}
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