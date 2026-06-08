import React from 'react';
import { IonContent, IonIcon, IonPage } from '@ionic/react';
import {
  arrowForwardOutline,
  documentTextOutline,
  flashOutline,
  lockClosedOutline,
  sparklesOutline,
} from 'ionicons/icons';
import { useHistory } from 'react-router-dom';
import './Home.css';

const HOME_CARDS = [
  {
    title: 'Citizen Documents',
    text: 'Translate complex government notices, property deeds, and certificates into plain, actionable language.',
    image: '/stitch/citizen-desk.png',
  },
  {
    title: 'Business Documents',
    text: 'Identify hidden risks in vendor contracts, master service agreements, and complex compliance filings instantly.',
    image: '/stitch/business-desk.png',
  },
  {
    title: 'Student Documents',
    text: 'Understand enrollment terms, student loan agreements, and academic notices with total clarity and confidence.',
    image: '/stitch/student-desk.png',
  },
];

const Home: React.FC = () => {
  const history = useHistory();

  return (
    <IonPage>
      <IonContent fullscreen>
        <div className="lexi-home">
          <nav className="lexi-home__nav">
            <div className="lexi-home__nav-inner">
              <div className="lexi-home__brand">
                <div className="lexi-home__brand-mark">
                  <IonIcon icon={documentTextOutline} />
                </div>
                <span className="lexi-home__brand-text">LexiNote</span>
              </div>

              <div className="lexi-home__nav-links">
                <a href="#solutions">Solutions</a>
                <a href="#security">Security</a>
                <a href="#pricing">Pricing</a>
                <a href="#about">About</a>
              </div>

              <div className="lexi-home__nav-actions">
                <button className="lexi-home__text-button" onClick={() => history.push('/features')}>
                  Sign In
                </button>
                <button className="lexi-home__primary-button lexi-home__primary-button--small" onClick={() => history.push('/features')}>
                  Get Started
                </button>
              </div>
            </div>
          </nav>

          <main className="lexi-home__main">
            <section className="lexi-home__hero" id="solutions">
              <div className="lexi-home__badge">
                <IonIcon icon={sparklesOutline} />
                <span>Next Generation Legal AI</span>
              </div>

              <h1 className="lexi-home__hero-title">
                Understand Legal Documents
                <br />
                with <span>Actionable AI</span>
              </h1>

              <p className="lexi-home__hero-copy">
                Upload agreements, notices, certificates, and legal records. Get plain-English explanations,
                risk analysis, obligations, and actionable recommendations.
              </p>

              <div className="lexi-home__hero-image-wrap">
                <img
                  src="/stitch/hero-illustration.png"
                  alt="LexiNote actionable legal insights hero"
                  className="lexi-home__hero-image"
                />
              </div>
            </section>

            <section className="lexi-home__drop-section">
              <div className="lexi-home__drop-card">
                <div className="lexi-home__drop-icon">
                  <IonIcon icon={documentTextOutline} />
                </div>
                <h2>Drop your documents here</h2>
                <p>Support for PDF, DOCX, and JPG (Max 50MB)</p>
                <div className="lexi-home__drop-tags">
                  <span>
                    <IonIcon icon={lockClosedOutline} />
                    Privacy First
                  </span>
                  <span>
                    <IonIcon icon={flashOutline} />
                    Instant Analysis
                  </span>
                </div>
                <button className="lexi-home__ghost-button" onClick={() => history.push('/features')}>
                  Open Upload Flow
                </button>
              </div>
            </section>

            <section className="lexi-home__cards-section" id="about">
              <div className="lexi-home__section-heading">
                <h2>Tailored for Every Need</h2>
                <p>
                  Specific AI models trained for distinct legal contexts to ensure the highest
                  accuracy in interpretation.
                </p>
              </div>

              <div className="lexi-home__cards-grid">
                {HOME_CARDS.map((card, index) => (
                  <article className="lexi-home__card" key={card.title}>
                    <div className="lexi-home__card-image-shell">
                      <img src={card.image} alt={card.title} className="lexi-home__card-image" />
                    </div>
                    <div className="lexi-home__card-body">
                      <div className="lexi-home__card-kicker">
                        {index === 0 ? 'Citizen Desk' : index === 1 ? 'Business Desk' : 'Student Desk'}
                      </div>
                      <h3>{card.title}</h3>
                      <p>{card.text}</p>
                      <button className="lexi-home__learn-button" onClick={() => history.push('/features')}>
                        Learn more
                        <IonIcon icon={arrowForwardOutline} />
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            </section>

            <section className="lexi-home__privacy-section" id="security">
              <div className="lexi-home__privacy-card">
                <div className="lexi-home__privacy-copy">
                  <h2>Your privacy is our legal obligation.</h2>
                  <p>
                    LexiNote utilizes enterprise-grade encryption and isolated processing
                    environments. Your documents are never used for training public models
                    without explicit consent.
                  </p>
                </div>
                <div className="lexi-home__privacy-actions">
                  <button className="lexi-home__light-button">Review Security Whitepaper</button>
                  <button className="lexi-home__dark-outline-button">Talk to Compliance</button>
                </div>
              </div>
            </section>
          </main>

          <footer className="lexi-home__footer" id="pricing">
            <div className="lexi-home__footer-inner">
              <div className="lexi-home__footer-brand">
                <div className="lexi-home__footer-logo">
                  <IonIcon icon={documentTextOutline} />
                </div>
                <div>
                  <div className="lexi-home__footer-title">LexiNote</div>
                  <div className="lexi-home__footer-copy">
                    © 2025 LexiNote AI Intelligence. All rights reserved.
                  </div>
                </div>
              </div>

              <div className="lexi-home__footer-links">
                <a href="#privacy">Privacy Policy</a>
                <a href="#terms">Terms of Service</a>
                <a href="#whitepaper">Security Whitepaper</a>
                <a href="#contact">Contact Support</a>
              </div>
            </div>
          </footer>
        </div>
      </IonContent>
    </IonPage>
  );
};

export default Home;
