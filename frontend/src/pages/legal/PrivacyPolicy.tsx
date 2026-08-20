import React from 'react';
import { Link } from 'react-router-dom';

const PrivacyPolicy: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto bg-white p-8 rounded-2xl shadow-sm border border-gray-100">
        <Link to="/" className="text-[var(--accent-indigo)] hover:underline mb-6 inline-block font-medium">
          &larr; Back to Home
        </Link>
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Privacy Policy</h1>
        <p className="text-sm text-gray-500 mb-8">Last Updated: March 2024</p>

        <div className="prose prose-indigo max-w-none text-gray-600">
          <p>
            Welcome to TeachGenie. We respect your privacy and are committed to protecting your personal data. 
            This privacy policy will inform you as to how we look after your personal data when you visit our website 
            and tell you about your privacy rights.
          </p>

          <h2 className="text-xl font-semibold text-gray-900 mt-8 mb-4">1. The data we collect about you</h2>
          <p>We may collect, use, store and transfer different kinds of personal data about you which we have grouped together as follows:</p>
          <ul className="list-disc pl-5 mt-2 space-y-1">
            <li><strong>Identity Data</strong> includes first name, last name, username or similar identifier, and your Google account information if you choose to log in with Google.</li>
            <li><strong>Contact Data</strong> includes email address.</li>
            <li><strong>Technical Data</strong> includes internet protocol (IP) address, your login data, browser type and version, time zone setting and location, browser plug-in types and versions, operating system and platform.</li>
            <li><strong>Usage Data</strong> includes information about how you use our website, uploaded PDFs, generated MCQs, and chat interactions with the AI.</li>
          </ul>

          <h2 className="text-xl font-semibold text-gray-900 mt-8 mb-4">2. How we use your personal data</h2>
          <p>We will only use your personal data when the law allows us to. Most commonly, we will use your personal data in the following circumstances:</p>
          <ul className="list-disc pl-5 mt-2 space-y-1">
            <li>Where we need to perform the contract we are about to enter into or have entered into with you (e.g., providing the AI study assistant services).</li>
            <li>Where it is necessary for our legitimate interests (or those of a third party) and your interests and fundamental rights do not override those interests.</li>
            <li>Where we need to comply with a legal obligation.</li>
          </ul>

          <h2 className="text-xl font-semibold text-gray-900 mt-8 mb-4">3. Data Security</h2>
          <p>
            We have put in place appropriate security measures to prevent your personal data from being accidentally lost, used, or accessed in an unauthorized way, altered, or disclosed. Your uploaded documents and chat histories are private to your account.
          </p>

          <h2 className="text-xl font-semibold text-gray-900 mt-8 mb-4">4. Third-party links</h2>
          <p>
            This website may include links to third-party websites, plug-ins, and applications. Clicking on those links or enabling those connections may allow third parties to collect or share data about you. We do not control these third-party websites and are not responsible for their privacy statements.
          </p>
        </div>
      </div>
    </div>
  );
};

export default PrivacyPolicy;
