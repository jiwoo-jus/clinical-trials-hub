import React from 'react';
// import { signInWithPopup, GoogleAuthProvider, signOut } from 'firebase/auth';
import { auth } from '../firebase';
import { useNavigate, useLocation } from 'react-router-dom';

function Header() {
  // const [user, setUser] = React.useState(null);
  const navigate = useNavigate();
  const location = useLocation();
  const isActive = (path) =>
  location.pathname === path
    ? 'text-blue-200 font-bold border-b-2 border-blue-300'
    : 'text-white border-b-2 border-transparent';
    
  React.useEffect(() => {
    const unsubscribe = auth.onAuthStateChanged((/* u */) => {
      // setUser(u);
    });
    return () => unsubscribe();
  }, []);

  // const handleSignIn = async () => {
  //   const provider = new GoogleAuthProvider();
  //   try {
  //     await signInWithPopup(auth, provider);
  //   } catch (err) {
  //     console.error('Error signing in:', err);
  //   }
  // };

  // const handleSignOut = async () => {
  //   try {
  //     await signOut(auth);
  //     window.location.reload();
  //   } catch (err) {
  //     console.error('Error signing out:', err);
  //   }
  // };

  // const handleViewHistory = () => {
  //   const historyJSON = sessionStorage.getItem('searchHistory');
  //   const historyData = historyJSON ? JSON.parse(historyJSON) : null;

  //   navigate('/history', { state: { historyData } });
  // };

  return (
    <header className="bg-gray-700 text-white py-4 px-6 flex items-center justify-between ">
      <div className="flex items-center space-x-6 pb-1">
        <button className={`text-sm py-1 font-semibold hover:border-blue-500 transition ${isActive("/")}`} onClick={() => window.location.href = "/"}>
              Home
        </button>
        <button className={`text-sm py-1 font-semibold hover:border-blue-500 transition ${isActive("/about")}`} onClick={() => navigate("/about")}>
          About
        </button>
        {/* {user && (
          <>
            
            <button className={`text-sm py-1 font-semibold hover:border-blue-500 transition ${isActive("/history")}`} onClick={handleViewHistory}>
              Recent Activity
            </button>
            <button className={`text-sm py-1 font-semibold hover:border-blue-500 transition ${isActive("/signout")}`}onClick={handleSignOut}>
              Sign Out
            </button>
          </>
        )} */}
      </div>

      {/* {user && <span className=" rounded border-gray-400 py-1 text-white h-full flex items-center px-4 text-sm font-medium">Hello, {user.displayName}</span> } */}

      {/* {!user && (
        <button className={`text-sm py-1 font-semibold hover:border-blue-500 transition ${isActive("/signin")}`} onClick={handleSignIn}>
          Sign In
        </button>
      )} */}
    </header>



  );
}

export default Header;