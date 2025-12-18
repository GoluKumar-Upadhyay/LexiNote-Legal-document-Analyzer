import React from 'react';
import {
  IonContent,
  IonPage,
  IonIcon
} from '@ionic/react';
import {
  documentTextOutline,
  personOutline,
  briefcaseOutline,
  schoolOutline,
  checkmarkCircleOutline,
  shieldCheckmarkOutline,
  timeOutline,
  analyticsOutline,
  bookOutline
} from 'ionicons/icons';
import { useHistory } from 'react-router-dom';

const FeaturesPage: React.FC = () => {
  const history = useHistory();

  return (
    <IonPage>
      <IonContent fullscreen style={{ background: '#f8fafc' }}>
        {/* Navigation */}
        <nav
          onClick={() => history.push('/home')}
          style={{
            background: '#ffffff',
            padding: '22px 48px',
            borderBottom: '1px solid #e5e7eb',
            display: 'flex',
            alignItems: 'center',
            gap: '14px',
            cursor: 'pointer'
          }}
        >
          <IonIcon icon={documentTextOutline} style={{ fontSize: '26px', color: '#2563eb' }} />
          <span style={{ fontSize: '22px', fontWeight: 600, color: '#0f172a' }}>
            LexiNote
          </span>
        </nav>

        {/* Page Content */}
        <section style={{ padding: '80px 48px' }}>
          <div style={{ maxWidth: '1280px', margin: '0 auto' }}>
            {/* Cards Grid */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
                gap: '36px'
              }}
            >
              <UserCard
                icon={personOutline}
                title="Citizens"
                category="citizen"
                subtitle="Know your rights clearly"
                history={history}
                description="Understand contracts, notices, and legal documents without confusion. LexiNote simplifies complex legal language into practical explanations aligned with Indian law."
                features={[
                  {
                    icon: checkmarkCircleOutline,
                    title: 'Plain language summaries',
                    desc: 'Legal terminology explained in simple, understandable words'
                  },
                  {
                    icon: shieldCheckmarkOutline,
                    title: 'Rights awareness',
                    desc: 'Understand protections available under Indian law'
                  },
                  {
                    icon: timeOutline,
                    title: 'Instant insights',
                    desc: 'Get document understanding within seconds'
                  }
                ]}
              />

              <UserCard
                icon={briefcaseOutline}
                title="Business Professionals"
                category="business"
                subtitle="Reduce risk. Save time."
                description="Review agreements, contracts, and policies efficiently. Identify risks, obligations, and compliance gaps before making business decisions."
                features={[
                  {
                    icon: analyticsOutline,
                    title: 'Contract intelligence',
                    desc: 'Structured analysis of clauses and obligations'
                  },
                  {
                    icon: shieldCheckmarkOutline,
                    title: 'Compliance verification',
                    desc: 'Cross-check documents against Indian legal acts'
                  },
                  {
                    icon: timeOutline,
                    title: 'Operational efficiency',
                    desc: 'Reduce dependency on manual legal reviews'
                  }
                ]}
                history={history}
              />

              <UserCard
                icon={schoolOutline}
                title="Students"
                category="student"
                subtitle="Learn faster, understand deeper"
                description="Break down judgments, case laws, and statutes into structured insights. Learn legal concepts with clarity and better retention."
                features={[
                  {
                    icon: bookOutline,
                    title: 'Case law breakdown',
                    desc: 'Judgments explained with context and structure'
                  },
                  {
                    icon: analyticsOutline,
                    title: 'Concept visualization',
                    desc: 'Simplified relationships between legal principles'
                  },
                  {
                    icon: checkmarkCircleOutline,
                    title: 'Research assistance',
                    desc: 'Faster access to relevant legal references'
                  }
                ]}
                history={history}
              />
            </div>
          </div>
        </section>
      </IonContent>
    </IonPage>
  );
};

interface UserCardProps {
  icon: string;
  title: string;
  subtitle: string;
  description: string;
  category: string;
  features: Array<{ icon: string; title: string; desc: string }>;
  history: any;
}

const UserCard: React.FC<UserCardProps> = ({
  icon,
  title,
  subtitle,
  description,
  features,
  category,
  history
}) => {
  return (
    <div
      onClick={() => history.push(`/upload/${category}`)}
      style={{
        background: '#ffffff',
        borderRadius: '16px',
        border: '1px solid #e5e7eb',
        padding: '36px',
        minHeight: '520px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        transition: 'box-shadow 0.25s ease',
        cursor: 'pointer'
      }}
      onMouseEnter={(e) =>
        (e.currentTarget.style.boxShadow =
          '0 14px 40px rgba(15, 23, 42, 0.08)')
      }
      onMouseLeave={(e) =>
        (e.currentTarget.style.boxShadow =
          '0 6px 20px rgba(15, 23, 42, 0.04)')
      }
    >
      {/* Header */}
      <div>
        <div
          style={{
            width: '52px',
            height: '52px',
            borderRadius: '12px',
            background: '#f1f5f9',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: '18px'
          }}
        >
          <IonIcon icon={icon} style={{ fontSize: '24px', color: '#1e293b' }} />
        </div>

        <h3 style={{ fontSize: '22px', fontWeight: 600, color: '#0f172a' }}>
          {title}
        </h3>
        <p style={{ fontSize: '15px', color: '#64748b', marginBottom: '20px' }}>
          {subtitle}
        </p>

        <p style={{ fontSize: '15px', lineHeight: '1.7', color: '#475569' }}>
          {description}
        </p>
      </div>

      {/* Features */}
      <div style={{ marginTop: '32px', display: 'flex', flexDirection: 'column', gap: '18px' }}>
        {features.map((f, i) => (
          <div key={i} style={{ display: 'flex', gap: '12px' }}>
            <IonIcon icon={f.icon} style={{ fontSize: '18px', color: '#2563eb' }} />
            <div>
              <div style={{ fontSize: '14px', fontWeight: 500, color: '#0f172a' }}>
                {f.title}
              </div>
              <div style={{ fontSize: '13px', color: '#64748b' }}>
                {f.desc}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default FeaturesPage;