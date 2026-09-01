import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import SEO from '../../components/SEO';
import { BookOpen } from 'lucide-react';
import { blogPosts } from '../../data/blogPosts';

const BlogIndexPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-[var(--bg-primary)]">
      <SEO 
        title="TeachGenie Blog - Study Tips & AI Learning"
        description="Read the latest articles on how to use AI for exam preparation, study smarter, and get the most out of your AI tutor."
        canonical="/blog"
      />
      
      <nav className="max-w-6xl mx-auto px-6 py-5 flex items-center justify-between border-b border-[var(--border)]">
        <div className="flex items-center gap-2 cursor-pointer" onClick={() => navigate('/')}>
          <BookOpen className="w-6 h-6 text-[var(--accent-green)]" />
          <span className="text-xl font-bold text-[var(--text-primary)]">TeachGenie</span>
        </div>
        <button onClick={() => navigate('/auth')} className="text-sm font-semibold bg-[var(--accent-green)] text-white px-5 py-2.5 rounded-xl hover:bg-green-700 transition-colors">
          Get Started
        </button>
      </nav>

      <main className="max-w-4xl mx-auto px-6 py-16">
        <h1 className="text-4xl md:text-5xl font-bold text-[var(--text-primary)] mb-6 text-center">
          The TeachGenie Blog
        </h1>
        <p className="text-lg text-[var(--text-secondary)] mb-16 text-center max-w-2xl mx-auto">
          Tips, guides, and insights on using AI to study smarter and score higher.
        </p>

        <div className="grid gap-8">
          {blogPosts.map((post) => (
            <Link key={post.slug} to={`/blog/${post.slug}`} className="block group">
              <div className="p-8 rounded-3xl bg-[var(--bg-secondary)] border border-[var(--border)] hover:border-[var(--accent-green)] transition-all">
                <p className="text-sm text-[var(--text-muted)] mb-3">{post.date}</p>
                <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-3 group-hover:text-[var(--accent-green)] transition-colors">
                  {post.title}
                </h2>
                <p className="text-[var(--text-secondary)]">
                  {post.description}
                </p>
              </div>
            </Link>
          ))}
        </div>
      </main>
    </div>
  );
};

export default BlogIndexPage;
