import React from 'react';
import { IonContent, IonHeader, IonPage, IonTitle, IonToolbar, IonButton, IonIcon, IonRouterContext,IonRouterLink } from '@ionic/react';
import { documentTextOutline, searchOutline, statsChartOutline, libraryOutline, videocamOutline, checkmarkCircle, people, shield } from 'ionicons/icons';

const Home: React.FC = () => {
  const scrollToSection = (sectionId: string) => {
    const element = document.getElementById(sectionId);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <IonPage>
      <IonContent fullscreen className="bb">
        <IonHeader collapse="condense">
          <IonToolbar style={{ '--background': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
            <IonTitle size="large" style={{ color: 'white' }}>LegalAI Analyzer</IonTitle>
          </IonToolbar>
        </IonHeader>

        {/* Navigation Bar */}
        <nav style={{
          background: 'white',
          padding: '20px 40px',
          boxShadow: '0 2px 10px rgba(0,0,0,0.05)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          position: 'sticky',
          top: 0,
          zIndex: 100
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }} onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
            <IonIcon icon={documentTextOutline} style={{ fontSize: '32px', color: '#667eea' }} />
            <span style={{ fontSize: '24px', fontWeight: 'bold', color: '#333' }}>LexiNote</span>
          </div>
          <div style={{ display: 'flex', gap: '30px', alignItems: 'center' }}>
            <a 
              onClick={() => scrollToSection('features')} 
              style={{ color: '#555', textDecoration: 'none', fontWeight: '500', cursor: 'pointer' }}
            >
              Features
            </a>
            <a 
              onClick={() => scrollToSection('how-it-works')} 
              style={{ color: '#555', textDecoration: 'none', fontWeight: '500', cursor: 'pointer' }}
            >
              How It Works
            </a>
            <a 
              onClick={() => scrollToSection('about')} 
              style={{ color: '#555', textDecoration: 'none', fontWeight: '500', cursor: 'pointer' }}
            >
              About
            </a>
            <IonRouterLink  routerLink='Features'><IonButton style={{ '--background': '#667eea' }} >
              Get Started
            </IonButton></IonRouterLink>
          </div>
        </nav>

        {/* Features Grid Section - MOVED UP */}
        <div id="features" style={{ padding: '100px 40px', background: 'white', scrollMarginTop: '80px' }}>
          <h2 style={{ textAlign: 'center', fontSize: '42px', fontWeight: 'bold', marginBottom: '20px', color: '#333', margin: '0 0 20px 0' }}>
            Comprehensive Features
          </h2>
          <p style={{ textAlign: 'center', fontSize: '18px', color: '#666', maxWidth: '700px', margin: '0 auto 80px' }}>
            Everything you need for intelligent legal document analysis
          </p>

          <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '30px' }}>
          <FeatureCard
              icon={documentTextOutline}
              title="Multi-LLM Analysis"
              description="Leverage multiple AI models simultaneously for comprehensive validation and enhanced accuracy."
              gradient="linear-gradient(135deg, #fa709a 0%, #fee140 100%)"
            />
            <FeatureCard
              icon={statsChartOutline}
              title="Mind Map Generation"
              description="Automatically generate visual mind maps to understand complex legal relationships and hierarchies."
              gradient="linear-gradient(135deg, #30cfd0 0%, #330867 100%)"
            />
            <FeatureCard
              icon={videocamOutline}
              title="AI Video Explanations"
              description="Get AI-generated video explanations that break down complex legal concepts into digestible content."
              gradient="linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)"
            />
            <FeatureCard
              icon={libraryOutline}
              title="Indian Kanoon Integration"
              description="Seamlessly cross-reference with India's largest legal database containing millions of case laws and statutes."
              gradient="linear-gradient(135deg, #f093fb 0%, #f5576c 100%)"
            />
            <FeatureCard
              icon={searchOutline}
              title="RAG Technology"
              description="Retrieval-Augmented Generation ensures contextually accurate and relevant legal analysis every time."
              gradient="linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)"
            />
            <FeatureCard
              icon={statsChartOutline}
              title="Vector Database"
              description="Lightning-fast semantic search powered by Pinecone for instant document retrieval and comparison."
              gradient="linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)"
            />
            
          </div>
        </div>

        {/* Tree Architecture Section - MOVED DOWN */}
        <div id="how-it-works" style={{ padding: '100px 40px', background: '#f8f9ff', scrollMarginTop: '80px' }}>
          <h2 style={{ textAlign: 'center', fontSize: '42px', fontWeight: 'bold', marginBottom: '20px', color: '#333', margin: '0 0 20px 0',fontFamily: "'Inter', sans-serif", }}>
            Working Platform
          </h2>
          <p style={{ textAlign: 'center', fontSize: '18px', color: '#666', maxWidth: '800px', margin: '0 auto 80px' ,fontFamily: "'Inter', sans-serif",}}>
            Our intelligent system connects multiple AI technologies to deliver comprehensive legal analysis
          </p>
          
          <div style={{
            position: 'relative',
            height: '650px',
            maxWidth: '1200px',
            margin: '0 auto',
          }}>
            {/* SVG Lines */}
            <svg
              viewBox="0 0 1000 600"
              style={{
                position: 'absolute',
                inset: 0,
                width: '100%',
                height: '100%',
                zIndex: 1,
              }}
            >
              <defs>
                <linearGradient id="lineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" style={{ stopColor: '#667eea', stopOpacity: 1 }} />
                  <stop offset="100%" style={{ stopColor: '#764ba2', stopOpacity: 1 }} />
                </linearGradient>
              </defs>
              <path d="M520 260 C 350 160, 220 120, 160 90" stroke="url(#lineGradient)" strokeWidth="3" fill="none" opacity="0.6" />
              <path d="M520 260 C 700 160, 820 120, 880 90" stroke="url(#lineGradient)" strokeWidth="3" fill="none" opacity="0.6" />
              <path d="M520 260 C 350 360, 220 440, 160 510" stroke="url(#lineGradient)" strokeWidth="3" fill="none" opacity="0.6" />
              <path d="M520 260 C 700 360, 820 440, 880 510" stroke="url(#lineGradient)" strokeWidth="3" fill="none" opacity="0.6" />
            </svg>

            {/* Center Logo */}
            <div style={{
              position: 'absolute',
              top: '210px',
              left: '50%',
              transform: 'translateX(-50%)',
              width: '180px',
              height: '180px',
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              boxShadow: '0 20px 60px rgba(102, 126, 234, 0.4)',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
              alignItems: 'center',
              zIndex: 2,
              color: 'white',
              scale:""

            }}>
              <IonIcon icon={documentTextOutline} style={{ fontSize: '48px' }} />
              <strong style={{ marginTop: '12px', fontSize: '20px' }}>LexiNote</strong>
              <span style={{ fontSize: '14px', opacity: 0.9 }}>Analyzer</span>  
            </div>

            {/* Feature Nodes */}
            <FeatureNode
              icon={libraryOutline}
              title="Indian Kanoon "
              subtitle="Legal Database"
              gradient="linear-gradient(135deg, #f093fb 0%, #f5576c 100%)"
              style={{ top: '40px', left: '40px' }}
            />

            <FeatureNode
              icon={searchOutline}
              title="AI Analyzer"
              subtitle="AI Legal Analyzer"
              gradient="linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)"
              style={{ top: '40px', right: '40px' }}
            />

            <FeatureNode
              icon={statsChartOutline}
              title="Indian Judgement record"
              subtitle="Cross check with Judgement data"
              gradient="linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)"
              style={{ bottom: '40px', left: '40px' }}
            />

            <FeatureNode
              icon={videocamOutline}
              title="AI Explanations"
              subtitle="Visual Understanding"
              gradient="linear-gradient(135deg, #fa709a 0%, #fee140 100%)"
              style={{ bottom: '40px', right: '40px' }}
            />
          </div>
        </div>

        {/* Why Choose Us Section */}
        <div id="about" style={{ padding: '100px 40px', background: 'white', scrollMarginTop: '80px' }}>
          <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '80px', alignItems: 'center' }}>
            <div>
              <h2 style={{ fontSize: '42px', fontWeight: 'bold', marginBottom: '20px', color: '#333', margin: '0 0 20px 0' }}>
                Why Choose LexiNote?
              </h2>
              <h3 style={{ fontSize: '28px', fontWeight: '600', color: '#667eea', marginBottom: '30px', margin: '0 0 30px 0', lineHeight: '1.4' }}>
                Transforming Legal Analysis with Advanced AI Technology
              </h3>
              <p style={{ fontSize: '18px', lineHeight: '1.8', color: '#555', marginBottom: '30px', margin: '0 0 30px 0' }}>
                Our platform combines cutting-edge AI technology with India's most comprehensive legal database. 
                We deliver unprecedented accuracy, speed, and insight into legal documents that would traditionally 
                take hours or days to analyze.
              </p>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <div style={{ display: 'flex', alignItems: 'start', gap: '15px' }}>
                  <IonIcon icon={checkmarkCircle} style={{ fontSize: '28px', color: '#43e97b', flexShrink: 0 }} />
                  <div>
                    <strong style={{ fontSize: '18px', color: '#333' }}>Validated Results</strong>
                    <p style={{ margin: '5px 0 0 0', color: '#666' }}>Every analysis is cross-verified with authoritative legal sources</p>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'start', gap: '15px' }}>
                  <IonIcon icon={shield} style={{ fontSize: '28px', color: '#4facfe', flexShrink: 0 }} />
                  <div>
                    <strong style={{ fontSize: '18px', color: '#333' }}>Secure & Confidential</strong>
                    <p style={{ margin: '5px 0 0 0', color: '#666' }}>Enterprise-grade security for all your legal documents</p>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'start', gap: '15px' }}>
                  <IonIcon icon={people} style={{ fontSize: '28px', color: '#fa709a', flexShrink: 0 }} />
                  <div>
                    <strong style={{ fontSize: '18px', color: '#333' }}>Expert Support</strong>
                    <p style={{ margin: '5px 0 0 0', color: '#666' }}>24/7 assistance from our team of legal tech specialists</p>
                  </div>
                </div>
              </div>
            </div>
            
            <div id="get-started" style={{
              background: '#f8f9ff',
              borderRadius: '20px',
              padding: '60px',
              boxShadow: '0 20px 60px rgba(0,0,0,0.1)',
              textAlign: 'center',
              scrollMarginTop: '80px'
            }}>
              <div style={{
                width: '120px',
                height: '120px',
                borderRadius: '50%',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 30px',
                boxShadow: '0 10px 30px rgba(102, 126, 234, 0.3)'
              }}>
                <IonIcon icon={documentTextOutline} style={{ fontSize: '56px', color: 'white' }} />
              </div>
              <h3 style={{ fontSize: '28px', fontWeight: 'bold', marginBottom: '15px', margin: '0 0 15px 0' }}>Ready to Get Started?</h3>
              <p style={{ fontSize: '16px', color: '#666', marginBottom: '30px', margin: '0 0 30px 0' }}>
                Join hundreds of legal professionals using LexiNote to transform their workflow
              </p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <footer style={{
          background: '#1a1a2e',
          color: 'white',
          padding: '80px 40px 30px'
        }}>
          <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '50px', marginBottom: '50px' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
                  <IonIcon icon={documentTextOutline} style={{ fontSize: '32px', color: '#667eea' }} />
                  <span style={{ fontSize: '24px', fontWeight: 'bold' }}>LexiNote</span>
                </div>
                <p style={{ opacity: 0.8, lineHeight: '1.6', margin: '0 0 20px 0' }}>
                  Empowering legal professionals with AI-driven document analysis and validation technology.
                </p>
                <div style={{ display: 'flex', gap: '15px' }}>
                  <div style={{ width: '40px', height: '40px', borderRadius: '50%', background: 'rgba(102, 126, 234, 0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}>
                    <span>f</span>
                  </div>
                  <div style={{ width: '40px', height: '40px', borderRadius: '50%', background: 'rgba(102, 126, 234, 0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}>
                    <span>in</span>
                  </div>
                  <div style={{ width: '40px', height: '40px', borderRadius: '50%', background: 'rgba(102, 126, 234, 0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}>
                    <span>tw</span>
                  </div>
                </div>
              </div>
              
              <div>
                <h4 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '20px', margin: '0 0 20px 0' }}>Product</h4>
                <ul style={{ listStyle: 'none', padding: 0, opacity: 0.8, lineHeight: '2.5', margin: 0 }}>
                  <li><a onClick={() => scrollToSection('features')} style={{ color: 'white', textDecoration: 'none', cursor: 'pointer' }}>Features</a></li>
                  <li style={{ color: 'white', textDecoration: 'none',cursor:'pointer' }}>Pricing</li>
                  <li style={{ color: 'white', textDecoration: 'none',cursor:'pointer' }}>API</li>
                  <li style={{ color: 'white', textDecoration: 'none',cursor:'pointer' }}>Integrations</li>
                </ul>
              </div>
              
              <div>
                <h4 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '20px', margin: '0 0 20px 0' }}>Company</h4>
                <ul style={{ listStyle: 'none', padding: 0, opacity: 0.8, lineHeight: '2.5', margin: 0 }}>
                  <li><a onClick={() => scrollToSection('')} style={{ color: 'white', textDecoration: 'none', cursor: 'pointer' }}>About Us</a></li>
                  <li style={{ color: 'white', textDecoration: 'none',cursor:'pointer' }}>Careers</li>
                  <li style={{ color: 'white', textDecoration: 'none',cursor:'pointer' }}>Blog</li>
                  <li style={{ color: 'white', textDecoration: 'none',cursor:'pointer' }}>Press Kit</li>
                </ul>
              </div>
              
              <div>
                <h4 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '20px', margin: '0 0 20px 0' }}>Support</h4>
                <ul style={{ listStyle: 'none', padding: 0, opacity: 0.8, lineHeight: '2.5', margin: 0 }}>
                  <li style={{ color: 'white', textDecoration: 'none',cursor:'pointer' }}>Help Center</li>
                  <li style={{ color: 'white', textDecoration: 'none',cursor:'pointer' }}>Contact Us</li>
                  <li style={{ color: 'white', textDecoration: 'none',cursor:'pointer' }}>Status</li>
                  <li style={{ color: 'white', textDecoration: 'none',cursor:'pointer' }}>FAQ </li>
                </ul>
              </div>
            </div>
            
            <div style={{
              borderTop: '1px solid rgba(255,255,255,0.1)',
              paddingTop: '30px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '20px',
              opacity: 0.7
            }}>
              <p style={{ margin: 0 }}>© 2024 LexiNote Analyzer. All rights reserved.</p>
              <div style={{ display: 'flex', gap: '30px' }}>
                <a href="#" style={{ color: 'white', textDecoration: 'none' }}>Privacy Policy</a>
                <a href="#" style={{ color: 'white', textDecoration: 'none' }}>Terms of Service</a>
                <a href="#" style={{ color: 'white', textDecoration: 'none' }}>Cookie Policy</a>
              </div>
            </div>
          </div>
        </footer>
      </IonContent>
    </IonPage>
  );
};

const FeatureNode = ({
  icon,
  title,
  subtitle,
  gradient,
  style,
}: {
  icon: string;
  title: string;
  subtitle: string;
  gradient: string;
  style: React.CSSProperties;
}) => {
  const [isHovered, setIsHovered] = React.useState(false);
  
  return (
    <div
      style={{
        position: 'absolute',
        display: 'flex',
        alignItems: 'center',
        gap: '14px',
        background: '#ffffff',
        padding: '18px 24px',
        borderRadius: '12px',
        boxShadow: isHovered ? '0 15px 35px rgba(0,0,0,0.15)' : '0 10px 25px rgba(0,0,0,0.08)',
        zIndex: 2,
        transform: isHovered ? 'scale(1.05)' : 'scale(1)',
        transition: 'all 0.3s ease',
        cursor: 'pointer',
        ...style,
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div style={{
        width: '50px',
        height: '50px',
        borderRadius: '10px',
        background: gradient,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0
      }}>
        <IonIcon icon={icon} style={{ fontSize: '26px', color: 'white' }} />
      </div>
      <div>
        <div style={{ fontSize: '16px', fontWeight: 600, color: '#333' }}>{title}</div>
        <div style={{ fontSize: '13px', color: '#6b7280' }}>{subtitle}</div>
      </div>
    </div>
  );
};

const FeatureCard = ({
  icon,
  title,
  description,
  gradient,
}: {
  icon: string;
  title: string;
  description: string;
  gradient: string;
}) => {
  const [isHovered, setIsHovered] = React.useState(false);

  return (
    <div 
      style={{
        background: 'white',
        borderRadius: '16px',
        padding: '35px',
        boxShadow: isHovered ? '0 20px 40px rgba(0,0,0,0.12)' : '0 5px 20px rgba(0,0,0,0.08)',
        transform: isHovered ? 'translateY(-8px)' : 'translateY(0)',
        transition: 'all 0.3s ease',
        cursor: 'pointer',
        border: '1px solid #f0f0f0'
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div style={{
        width: '65px',
        height: '65px',
        borderRadius: '12px',
        background: gradient,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        marginBottom: '20px'
      }}>
        <IonIcon icon={icon} style={{ fontSize: '32px', color: 'white' }} />
      </div>
      <h3 style={{ fontSize: '20px', fontWeight: 'bold', marginBottom: '12px', color: '#333', margin: '0 0 12px 0' }}>
        {title}
      </h3>
      <p style={{ color: '#666', lineHeight: '1.7', fontSize: '15px', margin: 0 }}>
        {description}
      </p>
    </div>
  );
};

export default Home;