import React from 'react';
import { Link } from 'react-router-dom';

const TermsOfService: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto bg-white p-8 rounded-2xl shadow-sm border border-gray-100">
        <Link to="/" className="text-[var(--accent-indigo)] hover:underline mb-6 inline-block font-medium">
          &larr; Back to Home
        </Link>
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Terms of Service</h1>
        <p className="text-sm text-gray-500 mb-8">Last Updated: March 2024</p>

        <div className="prose prose-indigo max-w-none text-gray-600">
          <p>
            Welcome to TeachGenie. By accessing or using our website and AI study assistant platform, you agree to be bound by these Terms of Service.
            If you disagree with any part of the terms, then you may not access the service.
          </p>

          <h2 className="text-xl font-semibold text-gray-900 mt-8 mb-4">1. Description of Service</h2>
          <p>
            TeachGenie provides an AI-powered study assistant for students. Our services include but are not limited to interacting with uploaded PDFs, generating MCQs, solving doubts, and providing study planning tools. 
            The AI responses are generated based on the content you provide and general AI training data.
          </p>

          <h2 className="text-xl font-semibold text-gray-900 mt-8 mb-4">2. User Accounts</h2>
          <p>
            When you create an account with us, you must provide information that is accurate, complete, and current at all times. 
            Failure to do so constitutes a breach of the Terms, which may result in immediate termination of your account on our Service.
            You are responsible for safeguarding the password that you use to access the Service and for any activities or actions under your password.
          </p>

          <h2 className="text-xl font-semibold text-gray-900 mt-8 mb-4">3. Fair Use & Restrictions</h2>
          <p>
            You agree not to use the Service for any unlawful purpose or any purpose prohibited under this clause. You agree not to:
          </p>
          <ul className="list-disc pl-5 mt-2 space-y-1">
            <li>Upload copyrighted material without permission.</li>
            <li>Use the Service to cheat on live, proctored examinations.</li>
            <li>Attempt to reverse engineer the AI systems or extract the source code.</li>
            <li>Overload the system with automated requests or scraping.</li>
          </ul>

          <h2 className="text-xl font-semibold text-gray-900 mt-8 mb-4">4. Limitation of Liability</h2>
          <p>
            While TeachGenie strives for high accuracy, AI can occasionally produce incorrect or hallucinatory responses. 
            TeachGenie is a supplemental study tool and should not be used as the absolute sole source of truth for critical exams or life decisions. 
            In no event shall TeachGenie, nor its directors, employees, partners, agents, suppliers, or affiliates, be liable for any indirect, incidental, special, consequential or punitive damages.
          </p>
        </div>
      </div>
    </div>
  );
};

export default TermsOfService;
