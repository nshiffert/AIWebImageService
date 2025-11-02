import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getStats } from '../api/client';
import type { StatsResponse } from '../types';
import { FiImage, FiCheckCircle, FiClock, FiTag, FiHardDrive } from 'react-icons/fi';

export const AdminDashboard = () => {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const data = await getStats();
      setStats(data);
    } catch (error) {
      console.error('Failed to load stats:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-gray-800 mb-8">Admin Dashboard</h1>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">
          <div className="bg-white p-6 rounded-lg shadow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 text-sm">Total Images</p>
                <p className="text-3xl font-bold text-gray-800">{stats?.total_images || 0}</p>
              </div>
              <FiImage className="text-4xl text-blue-600" />
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 text-sm">Approved</p>
                <p className="text-3xl font-bold text-green-600">{stats?.approved_images || 0}</p>
              </div>
              <FiCheckCircle className="text-4xl text-green-600" />
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 text-sm">Pending Review</p>
                <p className="text-3xl font-bold text-yellow-600">{stats?.pending_review || 0}</p>
              </div>
              <FiClock className="text-4xl text-yellow-600" />
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 text-sm">Total Tags</p>
                <p className="text-3xl font-bold text-purple-600">{stats?.total_tags || 0}</p>
              </div>
              <FiTag className="text-4xl text-purple-600" />
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 text-sm">Storage Used</p>
                <p className="text-3xl font-bold text-gray-800">
                  {stats?.storage_used_mb.toFixed(1) || 0} MB
                </p>
              </div>
              <FiHardDrive className="text-4xl text-gray-600" />
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Link
            to="/admin/generate"
            className="bg-blue-600 text-white p-8 rounded-lg shadow hover:bg-blue-700 transition text-center"
          >
            <h2 className="text-2xl font-bold mb-2">Generate Images</h2>
            <p>Create new AI-generated images</p>
          </Link>

          <Link
            to="/admin/review"
            className="bg-green-600 text-white p-8 rounded-lg shadow hover:bg-green-700 transition text-center"
          >
            <h2 className="text-2xl font-bold mb-2">Review Images</h2>
            <p>Approve or reject pending images</p>
          </Link>

          <Link
            to="/admin/settings"
            className="bg-purple-600 text-white p-8 rounded-lg shadow hover:bg-purple-700 transition text-center"
          >
            <h2 className="text-2xl font-bold mb-2">Settings</h2>
            <p>Configure meta prompt and preferences</p>
          </Link>
        </div>
      </div>
    </div>
  );
};
