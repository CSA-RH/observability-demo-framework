import React, { useState } from "react";
import { useKeycloak } from "@react-keycloak/web";

const Nav = () => {
 const { keycloak, initialized } = useKeycloak();
 const  [apiFeedback, setApiFeedback] = useState("Feedback Secure API call")

 const fetchData = async () => {
  try {
    const response = await fetch("http://127.0.0.1:8000/secured", {
      method: "GET",
      headers: {
        Authorization: `Bearer ${keycloak.token}`, // Attach the token
      },
    });

    if (!response.ok) {
      throw new Error(`Error: ${response.status}`);
    }

    const result = await response.json();
    console.log(result);
    setApiFeedback(Date.now() + ": " + result.user.name)
  } catch (err) {
    console.error(err.message);
    setApiFeedback(err.message);
  }
};

 return (
   <div>
     <div className="top-0 w-full flex flex-wrap">
       <section className="x-auto">
         <nav className="flex justify-between bg-gray-200 text-blue-800 w-screen">
           <div className="px-5 xl:px-12 py-6 flex w-full items-center">
             <h1 className="text-3xl font-bold font-heading">
               Keycloak React AUTH.
             </h1>
             <ul className="hidden md:flex px-4 mx-auto font-semibold font-heading space-x-12">
               <li>
                 <a className="hover:text-blue-800" href="/">
                   Home
                 </a>
               </li>
               <li>
                 <a className="hover:text-blue-800" href="/admin">
                   Admin Page
                 </a>
               </li>
               <li>
                 <a className="hover:text-blue-800" href="/user">
                   Secured Page
                 </a>
               </li>            
             </ul>
             <div className="hidden xl:flex items-center space-x-5">
               <div className="hover:text-gray-200">
                 {!keycloak.authenticated && (
                   <button
                     type="button"
                     className="text-blue-800"
                     onClick={() => keycloak.login()}
                   >
                     Login
                   </button>
                 )}

                 {!!keycloak.authenticated && (
                   <button
                     type="button"
                     className="text-blue-800"
                     onClick={() => keycloak.logout()}
                   >
                     Logout ({keycloak.tokenParsed.preferred_username})
                   </button>
                 )}
                 <div>
                  <button onClick={fetchData}>Test Secure API</button>
                 </div>
                 <div>
                  <span style={{ backgroundColor: "black", color: "white", margin: "5px" }}><b>{apiFeedback}</b></span>
                 </div>
               </div>
             </div>
           </div>
         </nav>
       </section>
     </div>
   </div>
 );
};

export default Nav;