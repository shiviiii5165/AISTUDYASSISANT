import React from 'react';
import { useParams, Navigate, useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import SEO from '../../components/SEO';
import { BookOpen, ArrowLeft } from 'lucide-react';
import { blogPosts } from '../../data/blogPosts';

const BlogPostPage: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  
  const post = blogPosts.find(p => p.slug === slug);
  
  if (!post) {
    return <Navigate to="/blog" replace />;
  }

  const articleSchema = {
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": post.title,
    "description": post.description,
    "author": {
      "@type": "Organization",
      "name": "LearnByGenie"
    },
    "publisher": {
      "@type": "Organization",
      "name": "LearnByGenie",
      "logo": {
        "@type": "ImageObject",
        "url": "https://teachgenie.online/logo.png"
      }
    },
    "datePublished": post.date,
  };

  return (
    <div className="min-h-[100dvh] bg-[var(--bg-primary)]">
      <SEO 
        title={post.title}
        description={post.description}
        canonical={`/blog/${post.slug}`}
        schema={articleSchema}
      />
      
      <nav className="max-w-6xl mx-auto px-6 py-5 flex items-center justify-between border-b border-[var(--border)]">
        <button type="button" aria-label="LearnByGenie home" className="flex items-center gap-2" onClick={() => navigate('/')}>
          <BookOpen className="w-6 h-6 text-[var(--accent-green)]" />
          <span className="text-xl font-bold text-[var(--text-primary)]">LearnByGenie</span>
        </button>
        <button onClick={() => navigate('/auth')} className="text-sm font-semibold bg-[var(--accent-green)] text-white px-5 py-2.5 rounded-xl hover:bg-[var(--accent-green-hover)] transition-colors">
          Get Started
        </button>
      </nav>

      <main className="max-w-3xl mx-auto px-6 py-12">
        <button onClick={() => navigate('/blog')} className="inline-flex items-center gap-2 text-[var(--text-primary)] hover:text-[var(--accent-green)] transition-colors mb-8">
          <ArrowLeft className="w-4 h-4" /> Back to Blog
        </button>
        
        <article className="prose prose-lg dark:prose-invert max-w-none prose-headings:text-[var(--text-primary)] prose-p:text-[var(--text-primary)] prose-a:text-[var(--accent-green)]">
          <ReactMarkdown>{post.content}</ReactMarkdown>
        </article>
      </main>
    </div>
  );
};

export default BlogPostPage;
