import { useState, useEffect } from 'react';
import { User, TrendingUp, Settings, CreditCard, AlertTriangle, Mail, Calendar, CheckCircle } from 'lucide-react';
import { useAuth } from '../App';
import { authAPI } from '../api';

export default function Profile() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('usage');
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editMode, setEditMode] = useState(false);
  const [name, setName] = useState('');

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      const response = await authAPI.get('/profile');
      setProfile(response.data);
      setName(response.data.name || user?.email?.split('@')[0] || 'User');
      setLoading(false);
    } catch (error) {
      console.error('Error fetching profile:', error);
      // Use fallback data
      setProfile({
        name: user?.email?.split('@')[0] || 'User',
        email: user?.email,
        tier: user?.tier || 'free',
        usage_month: 2,
        total_strategies: 2
      });
      setName(user?.email?.split('@')[0] || 'User');
      setLoading(false);
    }
  };

  const updateProfile = async () => {
    try {
      await authAPI.put('/profile', { name });
      setProfile({ ...profile, name });
      setEditMode(false);
    } catch (error) {
      console.error('Error updating profile:', error);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  const tabs = [
    { id: 'usage', label: 'Usage', icon: TrendingUp },
    { id: 'settings', label: 'Settings', icon: Settings },
    { id: 'billing', label: 'Billing', icon: CreditCard },
    { id: 'danger', label: 'Danger Zone', icon: AlertTriangle },
  ];

  return (
    <div className="min-h-screen p-6">
      <div className="max-w-5xl mx-auto">
        {/* Profile Header */}
        <div className="glass-card p-8 rounded-3xl mb-8 animate-fade-in">
          <div className="flex items-center gap-6">
            {/* Avatar */}
            <div className="w-24 h-24 rounded-full bg-gradient-to-br from-primary-600 to-accent-600 flex items-center justify-center text-white text-4xl font-bold shadow-2xl">
              {(profile?.name || 'U')[0].toUpperCase()}
            </div>
            
            {/* User Info */}
            <div className="flex-1">
              <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">
                {profile?.name || 'User'}
              </h1>
              <div className="flex items-center gap-3 flex-wrap">
                {/* Tier Badge */}
                {profile?.tier === 'pro' ? (
                  <span className="px-4 py-1.5 bg-gradient-to-r from-emerald-500 to-emerald-600 text-white rounded-full text-sm font-bold shadow-lg">
                    ✨ PRO MEMBER
                  </span>
                ) : (
                  <span className="px-4 py-1.5 bg-gray-600 text-white rounded-full text-sm font-semibold">
                    FREE TIER
                  </span>
                )}
                
                {/* Usage Badge */}
                <span className="text-gray-600 dark:text-gray-400 text-sm">
                  {profile?.usage_month || 0}/{profile?.tier === 'pro' ? '∞' : '3'} strategies this month
                </span>
              </div>
              
              {/* Email */}
              <div className="flex items-center gap-2 mt-3 text-gray-600 dark:text-gray-400">
                <Mail className="w-4 h-4" />
                <span>{profile?.email}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="glass-card rounded-3xl overflow-hidden mb-8">
          <div className="flex border-b border-gray-200 dark:border-gray-700">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex-1 flex items-center justify-center gap-2 px-6 py-4 font-medium transition-all ${
                    activeTab === tab.id
                      ? 'text-primary-600 dark:text-primary-400 border-b-3 border-primary-600 bg-primary-50 dark:bg-primary-900/20'
                      : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  <span className="hidden sm:inline">{tab.label}</span>
                </button>
              );
            })}
          </div>

          {/* Tab Content */}
          <div className="p-8">
            {activeTab === 'usage' && <UsageTab profile={profile} />}
            {activeTab === 'settings' && (
              <SettingsTab 
                profile={profile} 
                name={name}
                setName={setName}
                editMode={editMode}
                setEditMode={setEditMode}
                updateProfile={updateProfile}
              />
            )}
            {activeTab === 'billing' && <BillingTab profile={profile} />}
            {activeTab === 'danger' && <DangerZoneTab />}
          </div>
        </div>
      </div>
    </div>
  );
}

// Usage Tab Component
function UsageTab({ profile }) {
  const usageLimit = profile?.tier === 'pro' ? Infinity : 3;
  const usagePercent = profile?.tier === 'pro' ? 100 : ((profile?.usage_month || 0) / 3) * 100;

  return (
    <div className="space-y-6">
      {/* Usage Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* This Month */}
        <div className="glass-card p-6 rounded-2xl border-2 border-primary-200 dark:border-primary-800">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">This Month</h3>
            <Calendar className="w-6 h-6 text-primary-600" />
          </div>
          <p className="text-4xl font-bold text-primary-600 mb-2">
            {profile?.usage_month || 0}
          </p>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            of {profile?.tier === 'pro' ? 'unlimited' : '3'} strategies
          </p>
          {/* Progress Bar */}
          <div className="mt-4 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-primary-600 to-accent-600 transition-all"
              style={{ width: `${Math.min(usagePercent, 100)}%` }}
            />
          </div>
        </div>

        {/* Total Strategies */}
        <div className="glass-card p-6 rounded-2xl">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Total Created</h3>
            <CheckCircle className="w-6 h-6 text-emerald-600" />
          </div>
          <p className="text-4xl font-bold text-emerald-600 mb-2">
            {profile?.total_strategies || 0}
          </p>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            All time strategies
          </p>
        </div>

        {/* Account Status */}
        <div className="glass-card p-6 rounded-2xl">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Account Status</h3>
            <User className="w-6 h-6 text-accent-600" />
          </div>
          <p className="text-2xl font-bold text-accent-600 mb-2">
            {profile?.tier === 'pro' ? 'Premium' : 'Free'}
          </p>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {profile?.tier === 'pro' ? 'Unlimited access' : '3 strategies/month'}
          </p>
        </div>
      </div>

      {/* Upgrade CTA for Free Users */}
      {profile?.tier !== 'pro' && (
        <div className="glass-card p-6 rounded-2xl bg-gradient-to-r from-primary-50 to-accent-50 dark:from-primary-900/20 dark:to-accent-900/20 border-2 border-primary-200 dark:border-primary-800">
          <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
            Unlock Unlimited Strategies
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            Upgrade to Pro for unlimited AI-powered content strategies, priority support, and advanced features.
          </p>
          <a
            href="/upgrade"
            className="inline-block px-6 py-3 bg-gradient-to-r from-primary-600 to-accent-600 text-white rounded-xl font-semibold hover:shadow-lg transition-all"
          >
            Upgrade to Pro - ₹2,400/month
          </a>
        </div>
      )}
    </div>
  );
}

// Settings Tab Component
function SettingsTab({ profile, name, setName, editMode, setEditMode, updateProfile }) {
  return (
    <div className="space-y-6">
      <div className="glass-card p-6 rounded-2xl">
        <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-6">Profile Information</h3>
        
        <div className="space-y-4">
          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Display Name
            </label>
            {editMode ? (
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="input-premium"
                placeholder="Your name"
              />
            ) : (
              <p className="text-lg text-gray-900 dark:text-white">{profile?.name || 'Not set'}</p>
            )}
          </div>

          {/* Email (Read-only) */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Email Address
            </label>
            <p className="text-lg text-gray-600 dark:text-gray-400">{profile?.email}</p>
            <p className="text-xs text-gray-500 mt-1">Email cannot be changed</p>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 pt-4">
            {editMode ? (
              <>
                <button
                  onClick={updateProfile}
                  className="px-6 py-2 bg-gradient-to-r from-primary-600 to-accent-600 text-white rounded-xl font-semibold hover:shadow-lg transition-all"
                >
                  Save Changes
                </button>
                <button
                  onClick={() => {
                    setEditMode(false);
                    setName(profile?.name || '');
                  }}
                  className="px-6 py-2 glass-card rounded-xl font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-all"
                >
                  Cancel
                </button>
              </>
            ) : (
              <button
                onClick={() => setEditMode(true)}
                className="px-6 py-2 bg-gradient-to-r from-primary-600 to-accent-600 text-white rounded-xl font-semibold hover:shadow-lg transition-all"
              >
                Edit Profile
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Billing Tab Component
function BillingTab({ profile }) {
  return (
    <div className="space-y-6">
      {/* Current Plan */}
      <div className="glass-card p-6 rounded-2xl">
        <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-6">Current Plan</h3>
        
        <div className="flex items-center justify-between">
          <div>
            <p className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
              {profile?.tier === 'pro' ? 'Pro Plan' : 'Free Plan'}
            </p>
            <p className="text-gray-600 dark:text-gray-400">
              {profile?.tier === 'pro' 
                ? '₹2,400/month - Unlimited strategies' 
                : '3 strategies per month'}
            </p>
          </div>
          
          {profile?.tier === 'pro' ? (
            <span className="px-4 py-2 bg-gradient-to-r from-emerald-500 to-emerald-600 text-white rounded-full text-sm font-bold">
              Active
            </span>
          ) : (
            <a
              href="/upgrade"
              className="px-6 py-2 bg-gradient-to-r from-primary-600 to-accent-600 text-white rounded-xl font-semibold hover:shadow-lg transition-all"
            >
              Upgrade Now
            </a>
          )}
        </div>
      </div>

      {/* Billing Portal (Pro only) */}
      {profile?.tier === 'pro' && (
        <div className="glass-card p-6 rounded-2xl">
          <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-4">Manage Subscription</h3>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            Update payment method, view invoices, or cancel your subscription through the Razorpay portal.
          </p>
          <button
            onClick={() => window.open('https://razorpay.com', '_blank')}
            className="px-6 py-2 glass-card rounded-xl font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-all"
          >
            Open Billing Portal →
          </button>
        </div>
      )}
    </div>
  );
}

// Danger Zone Tab Component
function DangerZoneTab() {
  const [confirmDelete, setConfirmDelete] = useState(false);

  const handleDeleteAccount = () => {
    if (confirmDelete) {
      alert('Account deletion would happen here. This is a demo.');
      setConfirmDelete(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="glass-card p-6 rounded-2xl border-2 border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/10">
        <div className="flex items-start gap-4">
          <AlertTriangle className="w-6 h-6 text-red-600 flex-shrink-0 mt-1" />
          <div className="flex-1">
            <h3 className="text-xl font-bold text-red-600 dark:text-red-400 mb-2">Delete Account</h3>
            <p className="text-gray-700 dark:text-gray-300 mb-4">
              Once you delete your account, there is no going back. This will permanently delete all your strategies, usage history, and account data.
            </p>
            
            {!confirmDelete ? (
              <button
                onClick={() => setConfirmDelete(true)}
                className="px-6 py-2 bg-red-600 text-white rounded-xl font-semibold hover:bg-red-700 transition-all"
              >
                Delete Account
              </button>
            ) : (
              <div className="space-y-3">
                <p className="font-semibold text-red-600 dark:text-red-400">
                  Are you absolutely sure? This action cannot be undone.
                </p>
                <div className="flex gap-3">
                  <button
                    onClick={handleDeleteAccount}
                    className="px-6 py-2 bg-red-600 text-white rounded-xl font-semibold hover:bg-red-700 transition-all"
                  >
                    Yes, Delete My Account
                  </button>
                  <button
                    onClick={() => setConfirmDelete(false)}
                    className="px-6 py-2 glass-card rounded-xl font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-all"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
