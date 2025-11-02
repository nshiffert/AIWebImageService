import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { FiLogOut, FiHome, FiSettings } from 'react-icons/fi';

export const Navbar = () => {
  const { isAuthenticated, user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <nav className="bg-white shadow-md">
      <div className="container mx-auto px-4">
        <div className="flex justify-between items-center h-16">
          <Link to="/" className="flex items-center space-x-2">
            <span className="text-2xl font-bold text-blue-600">AI Image Library</span>
          </Link>

          <div className="flex items-center space-x-4">
            {isAuthenticated ? (
              <>
                <Link
                  to="/admin"
                  className="flex items-center space-x-1 text-gray-700 hover:text-blue-600 transition"
                >
                  <FiHome className="text-lg" />
                  <span>Dashboard</span>
                </Link>
                <Link
                  to="/admin/settings"
                  className="flex items-center space-x-1 text-gray-700 hover:text-blue-600 transition"
                >
                  <FiSettings className="text-lg" />
                  <span>Settings</span>
                </Link>
                <div className="flex items-center space-x-2">
                  <span className="text-sm text-gray-600">Hi, {user}</span>
                  <button
                    onClick={handleLogout}
                    className="flex items-center space-x-1 bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600 transition"
                  >
                    <FiLogOut />
                    <span>Logout</span>
                  </button>
                </div>
              </>
            ) : (
              <Link
                to="/login"
                className="bg-blue-500 text-white px-6 py-2 rounded hover:bg-blue-600 transition"
              >
                Login
              </Link>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
};
