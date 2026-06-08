import React from 'react';
import { IonButton, IonContent, IonIcon, IonPage } from '@ionic/react';
import {
  alertCircleOutline,
  arrowBackOutline,
  arrowForwardOutline,
  briefcaseOutline,
  documentTextOutline,
  personOutline,
  schoolOutline,
  shieldCheckmarkOutline,
} from 'ionicons/icons';
import { useHistory } from 'react-router-dom';
import { CATEGORY_CONFIG, CategoryKey } from '../data/categories';

const CARD_MEDIA: Record<CategoryKey, string> = {
  citizen: '/stitch/citizen-desk.png',
  business: '/stitch/business-desk.png',
  student: '/stitch/student-desk.png',
};

const CARD_PREVIEW: Record<CategoryKey, string> = {
  citizen: 'Generates simplified rights, obligations, notice deadlines, and citizen-side caution points.',
  business: 'Highlights clause risks, payment exposure, commercial obligations, and compliance gaps.',
  student: 'Explains internship, admission, scholarship, and academic-record duties in plain language.',
};

const CARD_DOCS: Record<CategoryKey, string[]> = {
  citizen: ['Rental agreement', 'Loan agreement', 'Property document'],
  business: ['Vendor agreement', 'NDA', 'Service contract'],
  student: ['Internship offer letter', 'Admission letter', 'Scholarship letter'],
};

const FeaturePage: React.FC = () => {
  const history = useHistory();

  const cards: Array<{ key: CategoryKey; icon: string }> = [
    { key: 'citizen', icon: personOutline },
    { key: 'business', icon: briefcaseOutline },
    { key: 'student', icon: schoolOutline },
  ];

  return (
    <IonPage>
      <IonContent fullscreen>
        <div style={{ minHeight: '100vh', background: 'radial-gradient(circle at top right, rgba(33, 112, 228, 0.08), transparent 30%), #f8f9ff' }}>
          <TopNav onBack={() => history.push('/home')} />

          <main style={{ maxWidth: '1440px', margin: '0 auto', padding: '36px 24px 88px' }}>
            <header style={{ maxWidth: '920px', margin: '0 auto 30px', textAlign: 'center' }}>
              <div
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '8px 14px',
                  borderRadius: '999px',
                  background: '#ffffff',
                  border: '1px solid #f1f5f9',
                  color: '#0058be',
                  fontWeight: 700,
                  fontSize: '12px',
                  letterSpacing: '0.06em',
                  textTransform: 'uppercase',
                  marginBottom: '18px',
                }}
              >
                <IonIcon icon={shieldCheckmarkOutline} />
                Guided mode active
              </div>

              <h1 style={{ margin: 0, color: '#0b1c30', fontSize: 'clamp(2.6rem, 4.6vw, 4.2rem)', lineHeight: 1.05, fontWeight: 600 }}>
                Choose your intelligence path
              </h1>
              <p style={{ margin: '18px auto 0', color: '#45464d', fontSize: '18px', lineHeight: 1.75, maxWidth: '760px' }}>
                Select the desk that matches the document. LexiNote will adapt its legal reasoning, accepted file rules, and warnings to that category before full analysis.
              </p>
            </header>

            <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '24px' }}>
              {cards.map((card) => {
                const config = CATEGORY_CONFIG[card.key];

                return (
                  <article
                    key={card.key}
                    style={{
                      background: 'rgba(255,255,255,0.72)',
                      backdropFilter: 'blur(12px)',
                      border: '1px solid #f1f5f9',
                      borderRadius: '32px',
                      padding: '16px',
                      boxShadow: '0 10px 30px -5px rgba(0, 0, 0, 0.04), 0 4px 10px -2px rgba(0, 0, 0, 0.02)',
                      display: 'flex',
                      flexDirection: 'column',
                      height: '100%',
                    }}
                  >
                    <div
                      style={{
                        borderRadius: '24px',
                        overflow: 'hidden',
                        background: '#e5eeff',
                        marginBottom: '18px',
                        aspectRatio: '1 / 1',
                      }}
                    >
                      <img
                        src={CARD_MEDIA[card.key]}
                        alt={`${config.title} illustration`}
                        style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
                      />
                    </div>

                    <div style={{ padding: '4px 8px 0', display: 'flex', flexDirection: 'column', flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', marginBottom: '10px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <IonIcon icon={card.icon} style={{ fontSize: '22px', color: '#0058be' }} />
                          <h2 style={{ margin: 0, color: '#0b1c30', fontSize: '28px', lineHeight: 1.15, fontWeight: 600 }}>{config.title}</h2>
                        </div>
                        <IonIcon icon={arrowForwardOutline} style={{ color: '#0058be', fontSize: '18px' }} />
                      </div>

                      <p style={{ margin: 0, color: '#45464d', lineHeight: 1.72, fontSize: '15px' }}>{config.subtitle}</p>

                      <div style={{ marginTop: '20px' }}>
                        <div style={{ color: '#7c839b', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.12em', fontWeight: 700, marginBottom: '10px' }}>
                          Accepted documents
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                          {CARD_DOCS[card.key].map((doc) => (
                            <span
                              key={doc}
                              style={{
                                background: 'rgba(211, 228, 254, 0.52)',
                                border: '1px solid rgba(198, 198, 205, 0.55)',
                                color: '#45464d',
                                padding: '7px 11px',
                                borderRadius: '999px',
                                fontSize: '12px',
                                fontWeight: 500,
                              }}
                            >
                              {doc}
                            </span>
                          ))}
                        </div>
                      </div>

                      <div
                        style={{
                          marginTop: '18px',
                          padding: '16px',
                          borderRadius: '18px',
                          background: 'rgba(33, 112, 228, 0.08)',
                          border: '1px solid rgba(33, 112, 228, 0.18)',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#0058be', marginBottom: '8px' }}>
                          <IonIcon icon={shieldCheckmarkOutline} style={{ fontSize: '16px' }} />
                          <span style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.12em', fontWeight: 700 }}>AI Preview</span>
                        </div>
                        <div style={{ color: '#0b1c30', fontSize: '14px', lineHeight: 1.65 }}>{CARD_PREVIEW[card.key]}</div>
                      </div>

                      <div
                        style={{
                          marginTop: '16px',
                          padding: '14px 16px',
                          borderRadius: '18px',
                          background: '#fff7ef',
                          border: '1px solid rgba(186, 26, 26, 0.12)',
                          color: '#7a4040',
                          display: 'flex',
                          gap: '10px',
                          lineHeight: 1.65,
                          fontSize: '14px',
                        }}
                      >
                        <IonIcon icon={alertCircleOutline} style={{ fontSize: '18px', marginTop: '2px', flexShrink: 0 }} />
                        <span>{config.warning}</span>
                      </div>

                      <IonButton
                        expand="block"
                        onClick={() => history.push(`/upload/${card.key}`)}
                        style={{
                          '--background': 'linear-gradient(180deg, #3b82f6 0%, #2563eb 100%)',
                          '--border-radius': '20px',
                          height: '56px',
                          fontWeight: 700,
                          marginTop: '22px',
                        }}
                      >
                        Open Section
                      </IonButton>
                    </div>
                  </article>
                );
              })}
            </section>
          </main>
        </div>
      </IonContent>
    </IonPage>
  );
};

const TopNav = ({ onBack }: { onBack: () => void }) => (
  <nav
    style={{
      position: 'sticky',
      top: 0,
      zIndex: 30,
      background: 'rgba(248, 249, 255, 0.82)',
      backdropFilter: 'blur(16px)',
      borderBottom: '1px solid rgba(198, 198, 205, 0.45)',
    }}
  >
    <div
      style={{
        maxWidth: '1440px',
        margin: '0 auto',
        padding: '16px 24px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: '16px',
        flexWrap: 'wrap',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <div
          style={{
            width: '46px',
            height: '46px',
            borderRadius: '14px',
            background: '#131b2e',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <IonIcon icon={documentTextOutline} style={{ color: '#ffffff', fontSize: '22px' }} />
        </div>
        <div>
          <div style={{ color: '#0b1c30', fontWeight: 700, fontSize: '22px', lineHeight: 1.1 }}>LexiNote</div>
          <div style={{ color: '#565e74', fontSize: '12px', letterSpacing: '0.08em', textTransform: 'uppercase' }}>Select Category</div>
        </div>
      </div>

      <IonButton
        fill="outline"
        onClick={onBack}
        style={{
          '--border-radius': '16px',
          '--border-color': '#c6c6cd',
          '--color': '#0b1c30',
          height: '48px',
          fontWeight: 600,
        }}
      >
        <IonIcon icon={arrowBackOutline} slot="start" />
        Back
      </IonButton>
    </div>
  </nav>
);

export default FeaturePage;
