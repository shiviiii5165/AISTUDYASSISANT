import React from 'react';
import { Link } from 'react-router-dom';

const CookiePolicy: React.FC = () => {
  return (
    <div className="min-h-[100dvh] bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto bg-white p-8 rounded-2xl shadow-sm border border-gray-100">
        <Link to="/" className="text-[var(--accent-green-text)] hover:underline mb-6 inline-block font-medium">
          &larr; Back to Home
        </Link>
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Cookie Policy</h1>
        <p className="text-sm text-gray-500 mb-8">Last Updated: March 2024</p>

        <div className="prose prose-indigo max-w-none text-gray-600">
          <p>
            This Cookie Policy explains how TeachGenie uses cookies and similar technologies to recognize you when you visit our website. 
            It explains what these technologies are and why we use them, as well as your rights to control our use of them.
          </p>

          <h2 className="text-xl font-semibold text-gray-900 mt-8 mb-4">What are cookies?</h2>
          <p>
            Cookies are small data files that are placed on your computer or mobile device when you visit a website. 
            Cookies are widely used by website owners in order to make their websites work, or to work more efficiently, 
            as well as to provide reporting information.
          </p>

          <h2 className="text-xl font-semibold text-gray-900 mt-8 mb-4">Why do we use cookies?</h2>
          <p>We use first and third-party cookies for several reasons. Some cookies are required for technical reasons in order for our website to operate, and we refer to these as "essential" or "strictly necessary" cookies.</p>
          
          <h3 className="text-lg font-medium text-gray-900 mt-6 mb-2">1. Essential Cookies</h3>
          <p>
            These cookies are strictly necessary to provide you with services available through our website and to use some of its features, such as access to secure areas. 
            For example, we use Supabase to securely manage your authentication sessions. Without these cookies, basic functions of the site would not work.
          </p>

          <h3 className="text-lg font-medium text-gray-900 mt-6 mb-2">2. Analytics and Customization Cookies</h3>
          <p>
            These cookies collect information that is used either in aggregate form to help us understand how our website is being used or how effective our marketing campaigns are, 
            or to help us customize our website for you. You have the right to disable these cookies via our Cookie Consent banner.
          </p>

          <h2 className="text-xl font-semibold text-gray-900 mt-8 mb-4">How can I control cookies?</h2>
          <p>
            You have the right to decide whether to accept or reject cookies. You can exercise your cookie rights by setting your preferences in the Cookie Consent Manager that appears on your first visit to TeachGenie.
          </p>
          <p className="mt-4">
            You can also set or amend your web browser controls to accept or refuse cookies. If you choose to reject cookies, you may still use our website though your access to some functionality and areas of our website may be restricted.
          </p>
        </div>
      </div>
    </div>
  );
};

export default CookiePolicy;
