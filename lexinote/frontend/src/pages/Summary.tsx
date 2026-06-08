import React, { useEffect, useMemo, useState } from 'react';
import {
  IonButton,
  IonButtons,
  IonContent,
  IonHeader,
  IonIcon,
  IonModal,
  IonPage,
  IonSelect,
  IonSelectOption,
  IonSpinner,
  IonTitle,
  IonToolbar,
} from '@ionic/react';
import {
  alertCircleOutline,
  arrowBackOutline,
  briefcaseOutline,
  bulbOutline,
  checkmarkCircleOutline,
  closeOutline,
  documentAttachOutline,
  documentTextOutline,
  downloadOutline,
  gitNetworkOutline,
  informationCircleOutline,
  peopleOutline,
  personOutline,
  scaleOutline,
  schoolOutline,
  shieldCheckmarkOutline,
  sparklesOutline,
  trophyOutline,
  videocamOutline,
  warningOutline,
} from 'ionicons/icons';
import { useHistory, useLocation } from 'react-router-dom';
import ReactFlow, { Background, Controls, Edge, MiniMap, Node, Position } from 'reactflow';
import 'reactflow/dist/style.css';
import { buildApiUrl, VIDEO_ENABLED } from '../config/api';
import { CATEGORY_CONFIG, CategoryKey } from '../data/categories';

interface LocationState {
  summaryData: any;
  extractedText: string;
  documentType: string;
  category: string;
  backPath?: string;
}

interface MindMapNode {
  id: string;
  label: string;
  details?: string;
  icon?: string;
  status: 'positive' | 'negative' | 'neutral' | 'info';
  secondaryLabel?: string;
  children?: MindMapNode[];
}

const SummaryPage: React.FC = () => {
  const history = useHistory();
  const location = useLocation<LocationState>();
  const [restoredState, setRestoredState] = useState<LocationState | null>(() => {
    if (location.state?.summaryData) {
      return location.state;
    }
    try {
      const raw = sessionStorage.getItem('lexinote-summary-state');
      return raw ? (JSON.parse(raw) as LocationState) : null;
    } catch {
      sessionStorage.removeItem('lexinote-summary-state');
      return null;
    }
  });
  const activeState = location.state?.summaryData ? location.state : restoredState;
  const { summaryData, extractedText, category, backPath } = activeState || {};

  useEffect(() => {
    if (!summaryData) {
      history.replace('/features');
    }
  }, [history, summaryData]);

  useEffect(() => {
    if (!location.state?.summaryData) return;
    sessionStorage.setItem('lexinote-summary-state', JSON.stringify(location.state));
    setRestoredState(location.state);
  }, [location.state]);

  const [mindMapData, setMindMapData] = useState<MindMapNode | null>(null);
  const [showMindMapModal, setShowMindMapModal] = useState(false);
  const [isGeneratingMindMap, setIsGeneratingMindMap] = useState(false);
  const [mindMapError, setMindMapError] = useState<string | null>(null);
  const [reactFlowNodes, setReactFlowNodes] = useState<Node[]>([]);
  const [reactFlowEdges, setReactFlowEdges] = useState<Edge[]>([]);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [showVideoModal, setShowVideoModal] = useState(false);
  const [isGeneratingVideo, setIsGeneratingVideo] = useState(false);
  const [videoError, setVideoError] = useState<string | null>(null);
  const [selectedLanguage, setSelectedLanguage] = useState('en');
  const [showLanguageSelector, setShowLanguageSelector] = useState(false);

  if (!summaryData) {
    return null;
  }

  const summary = summaryData.DocumentSummary || summaryData;
  const currentCategory = (summary.Category || category || 'citizen').toLowerCase() as CategoryKey;
  const config = CATEGORY_CONFIG[currentCategory] || CATEGORY_CONFIG.citizen;
  const resolvedBackPath = backPath || `/upload/${currentCategory}`;
  const meta = summary._meta || {};
  const header = summary.Header || {};
  const riskLevel = summary?.Confidence_and_Risk_Score?.Risk_Level || summary?.Risk_Level || 'Unknown';
  const confidence = summary?.Confidence_and_Risk_Score?.Confidence || summary?.Confidence_Score || 'N/A';

  const categoryIcon = useMemo(() => {
    switch (currentCategory) {
      case 'student':
        return schoolOutline;
      case 'business':
        return briefcaseOutline;
      default:
        return personOutline;
    }
  }, [currentCategory]);

  const reportFacts = useMemo(
    () => [
      { label: 'Document Name', value: header.Document_Name || header.Document_Type || header.Type || 'Not stated in the document' },
      { label: 'Document Type', value: header.Document_Type || header.Type || 'Not stated in the document' },
      { label: 'Purpose', value: header.Purpose || 'Not stated in the document' },
      { label: 'Date', value: header.Date || 'Not stated in the document' },
      { label: 'Jurisdiction', value: header.Jurisdiction || 'Not stated in the document' },
    ],
    [header],
  );

  const riskItems = useMemo(() => {
    if (Array.isArray(summary.Risk_and_Compliance)) return summary.Risk_and_Compliance;
    if (Array.isArray(summary?.Risk_and_Compliance?.Potential_Issues)) return summary.Risk_and_Compliance.Potential_Issues;
    return [];
  }, [summary]);

  const keySectionTitle = currentCategory === 'student'
    ? 'Rights & Fairness'
    : currentCategory === 'citizen'
      ? 'Rights & Obligations'
      : 'Risk & Compliance Analysis';

  const keySectionData =
    currentCategory === 'student'
      ? summary.Rights_and_Fairness
      : currentCategory === 'citizen'
        ? summary.Rights_and_Obligations || summary.Rights_and_Fairness
        : summary.Risk_and_Compliance;

  const getValue = (path: string, defaultValue: any = null) =>
    path.split('.').reduce((acc, part) => acc && acc[part], summary) || defaultValue;

  const handleGenerateMindMap = async () => {
    setIsGeneratingMindMap(true);
    setMindMapError(null);

    try {
      const response = await fetch(buildApiUrl('/generate_mindmap'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category: currentCategory, summary_json: summary }),
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }

      const data = await response.json();
      setMindMapData(data);
      const { nodes, edges } = convertMindMapToReactFlow(data);
      setReactFlowNodes(nodes);
      setReactFlowEdges(edges);
      setShowMindMapModal(true);
    } catch (error: any) {
      setMindMapError(error.message || 'Failed to generate mind map.');
    } finally {
      setIsGeneratingMindMap(false);
    }
  };

  const handleGenerateVideo = async (language: string = selectedLanguage) => {
    setIsGeneratingVideo(true);
    setVideoError(null);
    setShowLanguageSelector(false);

    try {
      const formData = new FormData();
      formData.append('summary_text', summary.Simple_Summary || summary.Overview || 'No summary available');
      formData.append('category', currentCategory);
      formData.append('language', language);

      const response = await fetch(buildApiUrl('/generate_video'), {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const message = await response.text();
        throw new Error(message || `API Error: ${response.status}`);
      }

      const data = await response.json();
      const resolvedUrl = data.video_path?.startsWith('/api/')
        ? `${buildApiUrl('')}${data.video_path.replace('/api', '')}`
        : data.video_path;

      setVideoUrl(resolvedUrl || data.video_url || data.url || null);
      setShowVideoModal(true);
    } catch (error: any) {
      setVideoError(error.message || 'Failed to generate video.');
    } finally {
      setIsGeneratingVideo(false);
    }
  };

  return (
    <IonPage>
      <IonContent fullscreen>
        <div style={{ minHeight: '100vh', background: '#f5f7f4' }}>
          <div style={{ height: '7px', background: 'linear-gradient(90deg, #ff9933 0%, #ffffff 50%, #138808 100%)' }} />

          <nav
            style={{
              background: '#ffffff',
              borderBottom: '1px solid #d4dfe8',
              padding: '18px 30px',
            }}
          >
            <div
              style={{
                maxWidth: '1280px',
                margin: '0 auto',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                gap: '18px',
                flexWrap: 'wrap',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                <div
                  style={{
                    width: '52px',
                    height: '52px',
                    borderRadius: '16px',
                    background: '#14324b',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <IonIcon icon={documentTextOutline} style={{ color: '#ffffff', fontSize: '24px' }} />
                </div>
                <div>
                  <div style={{ fontSize: '13px', textTransform: 'uppercase', letterSpacing: '0.12em', color: '#6a7a89' }}>{config.department}</div>
                  <div style={{ fontSize: '24px', fontWeight: 700, color: '#102235' }}>Professional Analysis Report</div>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                <IonButton
                  fill="outline"
                  onClick={() => history.replace(resolvedBackPath)}
                  style={{ '--border-radius': '14px', '--border-color': '#c2ced9', '--color': '#102235' }}
                >
                  <IonIcon icon={arrowBackOutline} slot="start" />
                  Back
                </IonButton>
                <IonButton
                  onClick={handleGenerateMindMap}
                  disabled={isGeneratingMindMap}
                  style={{ '--background': '#14324b', '--border-radius': '14px', fontWeight: 700 }}
                >
                  {isGeneratingMindMap ? <IonSpinner name="crescent" slot="start" /> : <IonIcon icon={gitNetworkOutline} slot="start" />}
                  Mind Map
                </IonButton>
                {VIDEO_ENABLED && (
                  <IonButton
                    onClick={() => setShowLanguageSelector(true)}
                    disabled={isGeneratingVideo}
                    style={{ '--background': '#0b6b57', '--border-radius': '14px', fontWeight: 700 }}
                  >
                    {isGeneratingVideo ? <IonSpinner name="crescent" slot="start" /> : <IonIcon icon={videocamOutline} slot="start" />}
                    Video
                  </IonButton>
                )}
              </div>
            </div>
          </nav>

          <main style={{ maxWidth: '1280px', margin: '0 auto', padding: '28px 24px 80px' }}>
            <section
              style={{
                background: '#ffffff',
                border: '1px solid #d4dfe8',
                borderRadius: '26px',
                overflow: 'hidden',
                boxShadow: '0 18px 40px rgba(16, 34, 53, 0.05)',
                marginBottom: '24px',
              }}
            >
              <div style={{ background: '#14324b', color: '#ffffff', padding: '12px 24px', fontSize: '14px', letterSpacing: '0.02em' }}>
                Structured legal review generated from the uploaded document
              </div>

              <div style={{ padding: '28px 24px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '24px', flexWrap: 'wrap', alignItems: 'flex-start' }}>
                  <div style={{ maxWidth: '760px' }}>
                    <div
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '8px',
                        padding: '8px 12px',
                        borderRadius: '999px',
                        background: config.surface,
                        color: config.accent,
                        fontWeight: 700,
                        fontSize: '12px',
                        marginBottom: '14px',
                      }}
                    >
                      <IonIcon icon={categoryIcon} />
                      {config.title}
                    </div>

                    <h1 style={{ margin: 0, fontSize: '36px', lineHeight: 1.12, color: '#102235' }}>
                      {header.Document_Name || header.Document_Type || header.Type || 'Legal Document Report'}
                    </h1>

                    <p style={{ margin: '16px 0 0', color: '#48576a', lineHeight: 1.8, fontSize: '17px' }}>
                      {summary.Simple_Summary || summary.Overview || 'Summary not available.'}
                    </p>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(135px, 1fr))', gap: '12px', minWidth: '310px' }}>
                    <MetricCard title="Confidence" value={String(confidence)} icon={shieldCheckmarkOutline} tone="#0b4f6c" />
                    <MetricCard
                      title="Risk Level"
                      value={String(riskLevel)}
                      icon={warningOutline}
                      tone={
                        String(riskLevel).toLowerCase().includes('high')
                          ? '#b91c1c'
                          : String(riskLevel).toLowerCase().includes('medium')
                            ? '#8a3b12'
                            : '#166534'
                      }
                    />
                    <MetricCard title="Section" value={config.badge} icon={categoryIcon} tone={config.accent} />
                    <MetricCard title="Provider" value={meta.provider_used || 'Unknown'} icon={sparklesOutline} tone="#48576a" />
                  </div>
                </div>
              </div>
            </section>

            <div style={{ display: 'flex', gap: '24px', alignItems: 'flex-start', flexWrap: 'wrap' }}>
              <div style={{ flex: '1 1 760px', minWidth: '0' }}>
                <ProfessionalSection title="Document Register" icon={documentTextOutline} accent={config.accent}>
                  <DefinitionGrid items={reportFacts} />
                </ProfessionalSection>

                {isMeaningful(summary.Overview) && (
                  <ProfessionalSection title="Executive Overview" icon={bulbOutline} accent={config.accent}>
                    <TextPanel text={summary.Overview} />
                  </ProfessionalSection>
                )}

                {isMeaningful(summary.Parties_Involved) && (
                  <ProfessionalSection title="Parties Involved" icon={peopleOutline} accent={config.accent}>
                    <DefinitionGrid items={objectToDefinitionItems(summary.Parties_Involved)} />
                  </ProfessionalSection>
                )}

                {isMeaningful(summary.Key_Terms) && (
                  <ProfessionalSection title="Key Terms & Conditions" icon={documentAttachOutline} accent={config.accent}>
                    <DefinitionGrid items={objectToDefinitionItems(summary.Key_Terms)} />
                  </ProfessionalSection>
                )}

                {isMeaningful(keySectionData) && (
                  <ProfessionalSection title={keySectionTitle} icon={currentCategory === 'business' ? alertCircleOutline : shieldCheckmarkOutline} accent={config.accent}>
                    {Array.isArray(keySectionData) ? (
                      <BulletGrid items={keySectionData} tone="neutral" />
                    ) : (
                      <DefinitionGrid items={objectToDefinitionItems(keySectionData)} />
                    )}
                  </ProfessionalSection>
                )}

                {currentCategory === 'business' && isMeaningful(summary.Clause_Insights) && (
                  <ProfessionalSection title="Clause Insights" icon={informationCircleOutline} accent={config.accent}>
                    <BulletGrid items={summary.Clause_Insights} tone="neutral" />
                  </ProfessionalSection>
                )}

                {currentCategory === 'citizen' && isMeaningful(summary.Validation_Status) && (
                  <ProfessionalSection title="Validation Status" icon={checkmarkCircleOutline} accent={config.accent}>
                    <DefinitionGrid items={objectToDefinitionItems(summary.Validation_Status)} />
                  </ProfessionalSection>
                )}

                {isMeaningful(summary.Recommendations) && (
                  <ProfessionalSection title="Recommendations" icon={trophyOutline} accent={config.accent}>
                    <BulletGrid items={summary.Recommendations} tone="positive" />
                  </ProfessionalSection>
                )}

                {isMeaningful(riskItems) && (
                  <ProfessionalSection title="Risk & Compliance Issues" icon={alertCircleOutline} accent="#8a3b12">
                    <BulletGrid items={riskItems} tone="warning" />
                  </ProfessionalSection>
                )}

                {renderApplicableLaws(getValue('Applicable_Laws_and_Acts') || getValue('Applicable_Laws'), config.accent)}

                {extractedText && (
                  <ProfessionalSection title="Original Text Reference" icon={documentTextOutline} accent={config.accent}>
                    <div
                      style={{
                        background: '#f7fafc',
                        border: '1px solid #d4dfe8',
                        borderRadius: '18px',
                        padding: '18px',
                        maxHeight: '360px',
                        overflowY: 'auto',
                        whiteSpace: 'pre-wrap',
                        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
                        fontSize: '13px',
                        color: '#334155',
                        lineHeight: 1.75,
                      }}
                    >
                      {extractedText}
                    </div>
                  </ProfessionalSection>
                )}
              </div>

              <aside style={{ flex: '1 1 300px', maxWidth: '340px', width: '100%', display: 'grid', gap: '18px' }}>
                <SidebarCard title="Report Notes" icon={shieldCheckmarkOutline}>
                  <SidebarLine label="Section" value={config.badge} />
                  <SidebarLine label="Provider" value={meta.provider_used || 'Unknown'} />
                  <SidebarLine label="Chunk Count" value={String(meta.chunk_count || 'N/A')} />
                  <SidebarLine label="Risk Level" value={String(riskLevel)} />
                </SidebarCard>

                <SidebarCard title="Reviewer Guidance" icon={informationCircleOutline}>
                  <p style={sidebarParagraphStyle}>
                    Treat this as a professional draft analysis. Recheck names, dates, money clauses, obligations, and missing terms before final use.
                  </p>
                </SidebarCard>

                <SidebarCard title="Document Fit" icon={categoryIcon}>
                  <p style={sidebarParagraphStyle}>
                    This report was prepared for the <strong>{config.badge}</strong> section. If the document actually belongs to another section, re-upload it there for a more relevant review.
                  </p>
                </SidebarCard>
              </aside>
            </div>
          </main>

          <IonModal isOpen={showLanguageSelector} onDidDismiss={() => setShowLanguageSelector(false)}>
            <IonHeader>
              <IonToolbar>
                <IonTitle>Choose Video Language</IonTitle>
                <IonButtons slot="end">
                  <IonButton onClick={() => setShowLanguageSelector(false)}>
                    <IonIcon icon={closeOutline} />
                  </IonButton>
                </IonButtons>
              </IonToolbar>
            </IonHeader>
            <IonContent>
              <div style={{ maxWidth: '460px', margin: '0 auto', padding: '40px 24px', textAlign: 'center' }}>
                <div style={{ fontSize: '16px', color: '#48576a', lineHeight: 1.75, marginBottom: '24px' }}>
                  Create a short presentation-style legal explainer from this summary.
                </div>
                <IonSelect value={selectedLanguage} onIonChange={(e) => setSelectedLanguage(e.detail.value)} interface="popover">
                  <IonSelectOption value="en">English</IonSelectOption>
                  <IonSelectOption value="hi">Hindi</IonSelectOption>
                  <IonSelectOption value="ta">Tamil</IonSelectOption>
                  <IonSelectOption value="te">Telugu</IonSelectOption>
                  <IonSelectOption value="kn">Kannada</IonSelectOption>
                  <IonSelectOption value="bn">Bengali</IonSelectOption>
                </IonSelect>
                <div style={{ display: 'flex', justifyContent: 'center', gap: '12px', marginTop: '24px' }}>
                  <IonButton fill="outline" onClick={() => setShowLanguageSelector(false)}>
                    Cancel
                  </IonButton>
                  <IonButton onClick={() => handleGenerateVideo(selectedLanguage)} style={{ '--background': '#0b6b57' }}>
                    Generate Video
                  </IonButton>
                </div>
              </div>
            </IonContent>
          </IonModal>

          <IonModal isOpen={showMindMapModal} onDidDismiss={() => setShowMindMapModal(false)} className="fullscreen-modal">
            <IonHeader>
              <IonToolbar>
                <IonTitle>Mind Map View</IonTitle>
                <IonButtons slot="end">
                  <IonButton onClick={() => setShowMindMapModal(false)}>
                    <IonIcon icon={closeOutline} />
                  </IonButton>
                </IonButtons>
              </IonToolbar>
            </IonHeader>
            <IonContent>
              {mindMapError ? (
                <ErrorState title="Mind map generation failed" message={mindMapError} retry={handleGenerateMindMap} />
              ) : mindMapData ? (
                <div style={{ height: 'calc(100vh - 56px)', padding: '14px' }}>
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      gap: '12px',
                      alignItems: 'center',
                      flexWrap: 'wrap',
                      padding: '10px 12px 14px',
                      color: '#48576a',
                      fontSize: '14px',
                    }}
                  >
                    <div>Interactive tree layout with grouped legal findings and dependencies.</div>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      <LegendPill label="Info" color="#0b4f6c" />
                      <LegendPill label="Positive" color="#166534" />
                      <LegendPill label="Warning" color="#b91c1c" />
                      <LegendPill label="Neutral" color="#6a7a89" />
                    </div>
                  </div>
                  <div style={{ height: 'calc(100% - 54px)', borderRadius: '20px', overflow: 'hidden', border: '1px solid #d4dfe8' }}>
                    <ReactFlow nodes={reactFlowNodes} edges={reactFlowEdges} fitView fitViewOptions={{ padding: 0.2 }} nodesDraggable style={{ background: '#f5f7f4' }}>
                      <Controls />
                      <Background color="#d4dfe8" gap={18} />
                      <MiniMap />
                    </ReactFlow>
                  </div>
                </div>
              ) : (
                <LoadingState label="Preparing mind map..." />
              )}
            </IonContent>
          </IonModal>

          <IonModal isOpen={showVideoModal} onDidDismiss={() => setShowVideoModal(false)} className="fullscreen-modal">
            <IonHeader>
              <IonToolbar>
                <IonTitle>Video Presentation</IonTitle>
                <IonButtons slot="end">
                  <IonButton onClick={() => setShowVideoModal(false)}>
                    <IonIcon icon={closeOutline} />
                  </IonButton>
                </IonButtons>
              </IonToolbar>
            </IonHeader>
            <IonContent>
              {videoError ? (
                <ErrorState title="Video generation failed" message={videoError} retry={() => handleGenerateVideo(selectedLanguage)} />
              ) : videoUrl ? (
                <div style={{ maxWidth: '920px', margin: '0 auto', padding: '32px 24px 56px', textAlign: 'center' }}>
                  <div
                    style={{
                      background: '#14324b',
                      borderRadius: '24px',
                      overflow: 'hidden',
                      marginBottom: '24px',
                      boxShadow: '0 18px 50px rgba(15, 23, 42, 0.12)',
                    }}
                  >
                    <video controls style={{ width: '100%', height: 'auto', maxHeight: '72vh' }} src={videoUrl}>
                      Your browser does not support the video tag.
                    </video>
                  </div>
                  <IonButton
                    onClick={() => {
                      const link = document.createElement('a');
                      link.href = videoUrl;
                      link.download = `lexinote-${currentCategory}-${Date.now()}.mp4`;
                      document.body.appendChild(link);
                      link.click();
                      document.body.removeChild(link);
                    }}
                    style={{ '--background': '#0b4f6c', '--border-radius': '14px' }}
                  >
                    <IonIcon icon={downloadOutline} slot="start" />
                    Download Video
                  </IonButton>
                </div>
              ) : (
                <LoadingState label="Preparing video..." />
              )}
            </IonContent>
          </IonModal>
        </div>
      </IonContent>
    </IonPage>
  );
};

function isMeaningful(value: any) {
  if (!value) return false;
  if (typeof value === 'string') return value.trim() !== '';
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === 'object') return Object.keys(value).length > 0;
  return true;
}

function labelize(key: string) {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatValue(value: any): string {
  if (value === null || value === undefined) return 'Not stated in the document';
  if (typeof value === 'string') return value.trim() || 'Not stated in the document';
  if (Array.isArray(value)) {
    return value
      .map((item) => {
        if (typeof item === 'string') return item;
        return Object.entries(item || {})
          .map(([key, nestedValue]) => `${labelize(key)}: ${formatValue(nestedValue)}`)
          .join(' | ');
      })
      .join('\n');
  }
  if (typeof value === 'object') {
    return Object.entries(value)
      .map(([key, nestedValue]) => `${labelize(key)}: ${formatValue(nestedValue)}`)
      .join('\n');
  }
  return String(value);
}

function objectToDefinitionItems(data: Record<string, any>) {
  return Object.entries(data || {}).map(([key, value]) => ({
    label: labelize(key),
    value: formatValue(value),
  }));
}

function normalizeItem(item: any) {
  if (typeof item === 'string') {
    return {
      title: item,
      body: '',
    };
  }

  if (item && typeof item === 'object') {
    const entries = Object.entries(item);
    const [firstKey, firstValue] = entries[0] || ['Item', ''];
    return {
      title: `${labelize(firstKey)}: ${formatValue(firstValue)}`,
      body: entries
        .slice(1)
        .map(([key, value]) => `${labelize(key)}: ${formatValue(value)}`)
        .join('\n'),
    };
  }

  return {
    title: String(item),
    body: '',
  };
}

function countLeafUnits(node: MindMapNode): number {
  if (!node.children?.length) return 1;
  return node.children.reduce((sum, child) => sum + countLeafUnits(child), 0);
}

function convertMindMapToReactFlow(rootNode: MindMapNode) {
  const nodes: Node[] = [];
  const edges: Edge[] = [];

  const statusColors: Record<string, string> = {
    positive: '#166534',
    negative: '#b91c1c',
    neutral: '#6a7a89',
    info: '#0b4f6c',
  };

  const backgroundColors: Record<string, string> = {
    positive: '#edf8f0',
    negative: '#fef2f2',
    neutral: '#f8fafc',
    info: '#eef6fb',
  };

  const xGap = 360;
  const yGap = 190;

  const layoutNode = (node: MindMapNode, depth: number, topUnit: number, path: string, parentId?: string): number => {
    const span = countLeafUnits(node);
    const centerUnit = topUnit + span / 2;
    const nodeId = node.id ? `${path}-${node.id}` : `${path}-node`;

    nodes.push({
      id: nodeId,
      type: 'default',
      position: {
        x: depth * xGap,
        y: centerUnit * yGap,
      },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      draggable: true,
      data: {
        label: (
          <div
            style={{
              minWidth: '250px',
              maxWidth: '310px',
              padding: '16px',
              borderRadius: '18px',
              background: backgroundColors[node.status] || '#ffffff',
              border: `2px solid ${statusColors[node.status] || '#d4dfe8'}`,
              boxShadow: '0 12px 24px rgba(16, 34, 53, 0.08)',
            }}
          >
            <div style={{ fontWeight: 700, color: '#102235', marginBottom: '8px', lineHeight: 1.4 }}>{node.label}</div>
            {node.secondaryLabel && (
              <div style={{ fontSize: '12px', color: statusColors[node.status] || '#6a7a89', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                {node.secondaryLabel}
              </div>
            )}
            {node.details && <div style={{ fontSize: '13px', color: '#48576a', lineHeight: 1.6 }}>{node.details}</div>}
          </div>
        ),
      },
    });

    if (parentId) {
      edges.push({
        id: `edge-${parentId}-${nodeId}`,
        source: parentId,
        target: nodeId,
        type: 'smoothstep',
        animated: false,
        style: { stroke: statusColors[node.status] || '#94a3b8', strokeWidth: 2.2 },
      });
    }

    let childTop = topUnit;
    node.children?.forEach((child, index) => {
      const childSpan = countLeafUnits(child);
      layoutNode(child, depth + 1, childTop, `${nodeId}-${index}`, nodeId);
      childTop += childSpan;
    });

    return span;
  };

  layoutNode(rootNode, 0, 0, 'root');
  return { nodes, edges };
}

const ProfessionalSection = ({
  title,
  icon,
  accent,
  children,
}: {
  title: string;
  icon: string;
  accent: string;
  children: React.ReactNode;
}) => (
  <section
    style={{
      background: '#ffffff',
      border: '1px solid #d4dfe8',
      borderRadius: '24px',
      padding: '22px',
      marginBottom: '20px',
      boxShadow: '0 18px 40px rgba(16, 34, 53, 0.05)',
    }}
  >
    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '18px' }}>
      <div
        style={{
          width: '40px',
          height: '40px',
          borderRadius: '14px',
          background: `${accent}14`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: accent,
        }}
      >
        <IonIcon icon={icon} style={{ fontSize: '20px' }} />
      </div>
      <h2 style={{ margin: 0, fontSize: '25px', color: '#102235' }}>{title}</h2>
    </div>
    {children}
  </section>
);

const DefinitionGrid = ({ items }: { items: Array<{ label: string; value: string }> }) => (
  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '14px' }}>
    {items.map((item) => (
      <div
        key={`${item.label}-${item.value}`}
        style={{
          background: '#f7fafc',
          border: '1px solid #d4dfe8',
          borderRadius: '18px',
          padding: '16px',
        }}
      >
        <div style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#6a7a89', marginBottom: '8px' }}>{item.label}</div>
        <div style={{ color: '#102235', lineHeight: 1.72, whiteSpace: 'pre-wrap' }}>{item.value}</div>
      </div>
    ))}
  </div>
);

const TextPanel = ({ text }: { text: string }) => (
  <div
    style={{
      background: '#f7fafc',
      border: '1px solid #d4dfe8',
      borderRadius: '18px',
      padding: '18px',
      color: '#334155',
      lineHeight: 1.85,
      whiteSpace: 'pre-wrap',
    }}
  >
    {text}
  </div>
);

const BulletGrid = ({ items, tone }: { items: any[]; tone: 'neutral' | 'positive' | 'warning' }) => {
  const toneMap = {
    neutral: {
      background: '#f7fafc',
      border: '#d4dfe8',
      marker: '#0b4f6c',
      text: '#334155',
    },
    positive: {
      background: '#edf8f0',
      border: '#cde8d5',
      marker: '#166534',
      text: '#254234',
    },
    warning: {
      background: '#fff7ef',
      border: '#f3c9ae',
      marker: '#b45309',
      text: '#7c2d12',
    },
  }[tone];

  return (
    <div style={{ display: 'grid', gap: '12px' }}>
      {items.map((item, index) => {
        const normalized = normalizeItem(item);
        return (
          <div
            key={`${normalized.title}-${index}`}
            style={{
              display: 'flex',
              gap: '12px',
              alignItems: 'flex-start',
              padding: '16px',
              borderRadius: '18px',
              border: `1px solid ${toneMap.border}`,
              background: toneMap.background,
            }}
          >
            <div
              style={{
                width: '30px',
                height: '30px',
                borderRadius: '999px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: toneMap.marker,
                color: '#ffffff',
                fontSize: '12px',
                fontWeight: 700,
                flexShrink: 0,
              }}
            >
              {tone === 'warning' ? '!' : index + 1}
            </div>
            <div style={{ color: toneMap.text, lineHeight: 1.72, whiteSpace: 'pre-wrap' }}>
              <div style={{ fontWeight: 700, color: '#102235', marginBottom: normalized.body ? '6px' : 0 }}>{normalized.title}</div>
              {normalized.body && <div>{normalized.body}</div>}
            </div>
          </div>
        );
      })}
    </div>
  );
};

function renderApplicableLaws(applicableLaws: any, accent: string) {
  if (!isMeaningful(applicableLaws)) return null;

  if (Array.isArray(applicableLaws)) {
    return (
      <ProfessionalSection title="Applicable Laws" icon={scaleOutline} accent={accent}>
        <BulletGrid items={applicableLaws} tone="neutral" />
      </ProfessionalSection>
    );
  }

  return (
    <ProfessionalSection title="Applicable Laws & Acts" icon={scaleOutline} accent={accent}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px' }}>
        <div style={lawCardStyle}>
          <div style={lawHeadingStyle}>Explicit Acts</div>
          {(applicableLaws.Explicit_Acts || []).map((act: any, index: number) => (
            <div key={index} style={{ marginBottom: '12px', color: '#334155', lineHeight: 1.65 }}>
              <div style={{ fontWeight: 700, color: '#102235' }}>{act.Act || act}</div>
              <div>{act.Relevance || act.Reason || ''}</div>
            </div>
          ))}
        </div>
        <div style={lawCardStyle}>
          <div style={lawHeadingStyle}>Implicit Acts</div>
          {(applicableLaws.Implicit_Acts || []).map((act: any, index: number) => (
            <div key={index} style={{ marginBottom: '12px', color: '#334155', lineHeight: 1.65 }}>
              <div style={{ fontWeight: 700, color: '#102235' }}>{act.Act || act}</div>
              <div>{act.Relevance || act.Reason || ''}</div>
            </div>
          ))}
        </div>
      </div>
    </ProfessionalSection>
  );
}

const SidebarCard = ({
  title,
  icon,
  children,
}: {
  title: string;
  icon: string;
  children: React.ReactNode;
}) => (
  <div
    style={{
      background: '#ffffff',
      border: '1px solid #d4dfe8',
      borderRadius: '22px',
      padding: '18px',
      boxShadow: '0 18px 40px rgba(16, 34, 53, 0.05)',
    }}
  >
    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
      <IonIcon icon={icon} style={{ color: '#0b4f6c', fontSize: '18px' }} />
      <div style={{ fontWeight: 700, color: '#102235' }}>{title}</div>
    </div>
    {children}
  </div>
);

const SidebarLine = ({ label, value }: { label: string; value: string }) => (
  <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', padding: '10px 0', borderBottom: '1px solid #edf1f5' }}>
    <span style={{ color: '#6a7a89', fontSize: '14px' }}>{label}</span>
    <span style={{ color: '#102235', fontWeight: 600, textAlign: 'right' }}>{value}</span>
  </div>
);

const MetricCard = ({
  title,
  value,
  icon,
  tone,
}: {
  title: string;
  value: string;
  icon: string;
  tone: string;
}) => (
  <div
    style={{
      border: '1px solid #d4dfe8',
      borderRadius: '18px',
      background: '#f7fafc',
      padding: '16px',
    }}
  >
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: tone, marginBottom: '10px' }}>
      <IonIcon icon={icon} />
      <span style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.08em' }}>{title}</span>
    </div>
    <div style={{ fontWeight: 700, color: '#102235', fontSize: '18px', lineHeight: 1.35 }}>{value}</div>
  </div>
);

const LegendPill = ({ label, color }: { label: string; color: string }) => (
  <span
    style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '6px',
      padding: '6px 10px',
      borderRadius: '999px',
      background: '#ffffff',
      border: '1px solid #d4dfe8',
      color: '#334155',
      fontSize: '12px',
      fontWeight: 600,
    }}
  >
    <span style={{ width: '9px', height: '9px', borderRadius: '999px', background: color, display: 'inline-block' }} />
    {label}
  </span>
);

const LoadingState = ({ label }: { label: string }) => (
  <div style={{ textAlign: 'center', padding: '56px 20px' }}>
    <IonSpinner name="crescent" style={{ width: '54px', height: '54px', marginBottom: '16px' }} />
    <div style={{ color: '#48576a' }}>{label}</div>
  </div>
);

const ErrorState = ({ title, message, retry }: { title: string; message: string; retry: () => void }) => (
  <div style={{ textAlign: 'center', padding: '56px 20px' }}>
    <IonIcon icon={warningOutline} style={{ fontSize: '60px', color: '#b91c1c', marginBottom: '16px' }} />
    <h2 style={{ color: '#102235', marginBottom: '10px' }}>{title}</h2>
    <p style={{ color: '#6a7a89', maxWidth: '560px', margin: '0 auto 22px', lineHeight: 1.7 }}>{message}</p>
    <IonButton onClick={retry} style={{ '--background': '#0b4f6c' }}>
      Try Again
    </IonButton>
  </div>
);

const lawCardStyle: React.CSSProperties = {
  borderRadius: '18px',
  border: '1px solid #d4dfe8',
  background: '#f7fafc',
  padding: '18px',
};

const lawHeadingStyle: React.CSSProperties = {
  fontWeight: 700,
  color: '#102235',
  marginBottom: '12px',
};

const sidebarParagraphStyle: React.CSSProperties = {
  margin: 0,
  color: '#48576a',
  lineHeight: 1.75,
  fontSize: '14px',
};

export default SummaryPage;
