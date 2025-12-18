import React, { useState } from 'react';
import {
  IonContent,
  IonPage,
  IonIcon,
  IonButton,
  IonSelect,
  IonSelectOption,
  IonSpinner,
  IonModal,
  IonHeader,
  IonToolbar,
  IonTitle,
  IonButtons,
  IonFooter
} from '@ionic/react';
import {
  documentTextOutline,
  arrowBackOutline,
  sparklesOutline,
  listOutline,
  bulbOutline,
  checkmarkCircleOutline,
  shieldCheckmarkOutline,
  alertCircleOutline,
  peopleOutline,
  documentAttachOutline,
  warningOutline,
  trophyOutline,
  schoolOutline,
  businessOutline,
  personOutline,
  timeOutline,
  cashOutline,
  handRightOutline,
  closeCircleOutline,
  scaleOutline,
  playCircleOutline,
  closeOutline,
  downloadOutline,
  gitNetworkOutline,
  videocamOutline
} from 'ionicons/icons';
import { useHistory, useLocation } from 'react-router-dom';
import ReactFlow, { Node, Edge, Controls, Background, MiniMap } from 'reactflow';
import 'reactflow/dist/style.css';

interface LocationState {
  summaryData: any;
  extractedText: string;
  documentType: string;
  category: string;
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
  
  const { summaryData, extractedText, documentType, category } = location.state || {};

  // State for Mind Map
  const [mindMapData, setMindMapData] = useState<MindMapNode | null>(null);
  const [showMindMapModal, setShowMindMapModal] = useState(false);
  const [isGeneratingMindMap, setIsGeneratingMindMap] = useState(false);
  const [mindMapError, setMindMapError] = useState<string | null>(null);
  const [reactFlowNodes, setReactFlowNodes] = useState<Node[]>([]);
  const [reactFlowEdges, setReactFlowEdges] = useState<Edge[]>([]);

  // State for Video
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [showVideoModal, setShowVideoModal] = useState(false);
  const [isGeneratingVideo, setIsGeneratingVideo] = useState(false);
  const [videoError, setVideoError] = useState<string | null>(null);
  const [selectedLanguage, setSelectedLanguage] = useState('en');
  const [showLanguageSelector, setShowLanguageSelector] = useState(false);

  // If no data, redirect back
  if (!summaryData) {
    history.goBack();
    return null;
  }

  // Extract DocumentSummary object
  const summary = summaryData.DocumentSummary || summaryData;
  const currentCategory = summary.Category || category || 'citizen';

  // Get risk level color
  const getRiskColor = (risk: string) => {
    const riskLower = risk?.toLowerCase() || '';
    if (riskLower.includes('high')) return { bg: '#fef2f2', border: '#fca5a5', text: '#dc2626' };
    if (riskLower.includes('medium')) return { bg: '#fef3c7', border: '#fcd34d', text: '#ca8a04' };
    return { bg: '#f0fdf4', border: '#86efac', text: '#16a34a' };
  };

  // Get category icon and color
  const getCategoryInfo = () => {
    switch (currentCategory.toLowerCase()) {
      case 'student':
        return { 
          icon: schoolOutline, 
          color: '#8b5cf6',
          gradient: 'linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%)'
        };
      case 'business':
        return { 
          icon: businessOutline, 
          color: '#0ea5e9',
          gradient: 'linear-gradient(135deg, #0ea5e9 0%, #0369a1 100%)'
        };
      default: // citizen
        return { 
          icon: personOutline, 
          color: '#10b981',
          gradient: 'linear-gradient(135deg, #10b981 0%, #047857 100%)'
        };
    }
  };

  // Helper to safely get nested values
  const getValue = (path: string, defaultValue: any = null) => {
    return path.split('.').reduce((acc, part) => acc && acc[part], summary) || defaultValue;
  };

  // Check if value exists and should be displayed
  const shouldDisplay = (value: any) => {
    if (!value) return false;
    if (typeof value === 'string' && value.trim() === '') return false;
    if (Array.isArray(value) && value.length === 0) return false;
    if (typeof value === 'object' && Object.keys(value).length === 0) return false;
    return true;
  };

  // Get icon for field based on key
  const getFieldIcon = (key: string) => {
    const keyLower = key.toLowerCase();
    if (keyLower.includes('date') || keyLower.includes('time')) return timeOutline;
    if (keyLower.includes('payment') || keyLower.includes('stipend') || keyLower.includes('cash')) return cashOutline;
    if (keyLower.includes('right')) return handRightOutline;
    if (keyLower.includes('terminat') || keyLower.includes('exit') || keyLower.includes('close')) return closeCircleOutline;
    if (keyLower.includes('law') || keyLower.includes('act') || keyLower.includes('compliance')) return scaleOutline;
    return documentTextOutline;
  };

  /// ============== MIND MAP API HANDLER ==============
  const handleGenerateMindMap = async () => {
    setIsGeneratingMindMap(true);
    setMindMapError(null);
    
    try {
      const response = await fetch('http://127.0.0.1:5002/generate_mindmap', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          category: currentCategory.toLowerCase(),
          summary_json: summary
        })
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }

      const data = await response.json();
      setMindMapData(data);
      
      // Convert mind map data to React Flow format with proper layout
      const { nodes, edges } = convertMindMapToReactFlow(data);
      setReactFlowNodes(nodes);
      setReactFlowEdges(edges);
      
      setShowMindMapModal(true);
    } catch (error: any) {
      console.error('Mind map generation failed:', error);
      setMindMapError(error.message || 'Failed to generate mind map. Please try again.');
    } finally {
      setIsGeneratingMindMap(false);
    }
  };

  // Convert hierarchical mind map to React Flow nodes and edges with proper layout
  const convertMindMapToReactFlow = (rootNode: MindMapNode) => {
    const nodes: Node[] = [];
    const edges: Edge[] = [];
    
    // Determine node color based on status
    const statusColors: any = {
      positive: '#10b981',
      negative: '#ef4444',
      neutral: '#64748b',
      info: '#3b82f6'
    };

    const bgColors: any = {
      positive: '#f0fdf4',
      negative: '#fef2f2',
      neutral: '#f8fafc',
      info: '#eff6ff'
    };

    // Calculate hierarchical layout positions
    let nodeCounter = 0;
    const levelHeight = 200; // Vertical spacing between levels
    const nodeWidth = 350;   // Horizontal spacing between nodes

    const processNode = (node: MindMapNode, level: number, parentId?: string, indexInLevel: number = 0, siblingsCount: number = 1): string => {
      nodeCounter++;
      const nodeId = node.id || `node-${nodeCounter}`;
      
      // Calculate position for hierarchical left-to-right layout
      const xPos = level * nodeWidth;
      const yPos = indexInLevel * levelHeight;

      // Create the node with custom styling
      nodes.push({
        id: nodeId,
        type: 'default',
        position: { x: xPos, y: yPos },
        data: {
          label: (
            <div style={{
              padding: '16px',
              background: bgColors[node.status] || '#ffffff',
              border: `2px solid ${statusColors[node.status] || '#e5e7eb'}`,
              borderRadius: '12px',
              minWidth: '250px',
              maxWidth: '300px',
              cursor: 'grab'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                <div style={{ fontSize: '20px' }}>
                  {node.icon === 'document' && '📄'}
                  {node.icon === 'law' && '⚖️'}
                  {node.icon === 'people' && '👥'}
                  {node.icon === 'risk_high' && '⚠️'}
                  {node.icon === 'risk_low' && '✅'}
                  {node.icon === 'check' && '✓'}
                  {node.icon === 'money' && '💰'}
                  {node.icon === 'time' && '⏰'}
                  {node.icon === 'info' && 'ℹ️'}
                  {node.icon === 'recommendation' && '💡'}
                  {node.icon === 'star' && '⭐'}
                </div>
                <div>
                  <div style={{ fontWeight: 700, fontSize: '16px', color: '#0f172a' }}>
                    {node.label}
                  </div>
                  {node.secondaryLabel && (
                    <div style={{ fontSize: '12px', color: statusColors[node.status] || '#64748b', fontWeight: 600 }}>
                      {node.secondaryLabel}
                    </div>
                  )}
                </div>
              </div>
              {node.details && node.details !== 'N/A' && (
                <div style={{ fontSize: '13px', color: '#64748b', lineHeight: '1.5' }}>
                  {node.details}
                </div>
              )}
            </div>
          )
        },
        draggable: true
      });

      // Create edge if there's a parent
      if (parentId) {
        edges.push({
          id: `edge-${parentId}-${nodeId}`,
          source: parentId,
          target: nodeId,
          type: 'smoothstep',
          animated: true,
          style: { stroke: statusColors[node.status] || '#94a3b8', strokeWidth: 2 }
        });
      }

      // Recursively process children
      if (node.children && node.children.length > 0) {
        node.children.forEach((child, index) => {
          processNode(child, level + 1, nodeId, index, node.children!.length);
        });
      }

      return nodeId;
    };

    // Start processing from root
    processNode(rootNode, 0);

    return { nodes, edges };
  };
  // ============== VIDEO API HANDLER ==============
  const handleGenerateVideo = async (language: string = selectedLanguage) => {
    setIsGeneratingVideo(true);
    setVideoError(null);
    setShowLanguageSelector(false);
    
    try {
      const formData = new FormData();
      const summaryText = summary.Simple_Summary || summary.Overview || 'No summary available';
      
      formData.append('summary_text', summaryText);
      formData.append('category', currentCategory.toLowerCase());
      formData.append('language', language);

      const response = await fetch('http://127.0.0.1:5003/generate_video', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }

      const data = await response.json();
      
      // Adjust based on your API response structure
      const videoUrlFromApi = data.video_url || data.url || data.video_path;
      
      if (!videoUrlFromApi) {
        throw new Error('No video URL in response');
      }
      
      setVideoUrl(videoUrlFromApi);
      setShowVideoModal(true);
    } catch (error: any) {
      console.error('Video generation failed:', error);
      setVideoError(error.message || 'Failed to generate video. Please try again.');
    } finally {
      setIsGeneratingVideo(false);
    }
  };

  // Show language selector before video generation
  const handleVideoButtonClick = () => {
    setShowLanguageSelector(true);
  };

  // ============== RENDER FUNCTIONS ==============

  // Render object as key-value pairs
  const renderObject = (obj: any, title: string, icon: any, customStyles?: React.CSSProperties) => {
    if (!shouldDisplay(obj)) return null;
    
    const entries = Object.entries(obj);
    
    return (
      <div
        style={{
          background: '#ffffff',
          borderRadius: '16px',
          padding: '32px',
          border: '1px solid #e5e7eb',
          ...customStyles
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
          <IonIcon icon={icon} style={{ fontSize: '24px', color: getCategoryInfo().color }} />
          <h2 style={{ fontSize: '22px', fontWeight: 600, color: '#0f172a', margin: 0 }}>
            {title}
          </h2>
        </div>

        <div style={{ display: 'grid', gap: '16px' }}>
          {entries.map(([key, value]) => (
            <div key={key} style={{ paddingBottom: '16px', borderBottom: '1px solid #f1f5f9' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <IonIcon 
                  icon={getFieldIcon(key)} 
                  style={{ fontSize: '16px', color: '#94a3b8' }} 
                />
                <div style={{ fontSize: '13px', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  {key.replace(/_/g, ' ')}
                </div>
              </div>
              <div style={{ fontSize: '14px', color: '#475569', lineHeight: '1.7', paddingLeft: '24px' }}>
                {typeof value === 'string' ? value : JSON.stringify(value, null, 2)}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  // Render array as list
  const renderList = (items: any[], title: string, icon: any, isWarning: boolean = false, customStyles?: React.CSSProperties) => {
    if (!shouldDisplay(items)) return null;

    return (
      <div
        style={{
          background: '#ffffff',
          borderRadius: '16px',
          padding: '32px',
          border: `1px solid ${isWarning ? '#fca5a5' : '#e5e7eb'}`,
          ...customStyles
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
          <IonIcon icon={icon} style={{ fontSize: '24px', color: isWarning ? '#ef4444' : getCategoryInfo().color }} />
          <h2 style={{ fontSize: '22px', fontWeight: 600, color: '#0f172a', margin: 0 }}>
            {title}
          </h2>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {items.map((item, index) => (
            <div
              key={index}
              style={{
                padding: '16px',
                background: isWarning ? '#fef2f2' : '#f8fafc',
                borderRadius: '8px',
                border: `1px solid ${isWarning ? '#fca5a5' : '#e2e8f0'}`,
                display: 'flex',
                gap: '12px',
                alignItems: 'flex-start'
              }}
            >
              {isWarning ? (
                <div
                  style={{
                    minWidth: '24px',
                    height: '24px',
                    borderRadius: '50%',
                    background: '#dc2626',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '12px',
                    fontWeight: 700,
                    color: '#ffffff',
                    flexShrink: 0,
                    marginTop: '2px'
                  }}
                >
                  !
                </div>
              ) : (
                <div
                  style={{
                    minWidth: '24px',
                    height: '24px',
                    borderRadius: '6px',
                    background: getCategoryInfo().color,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '12px',
                    fontWeight: 600,
                    color: '#ffffff',
                    flexShrink: 0,
                    marginTop: '2px'
                  }}
                >
                  {index + 1}
                </div>
              )}
              <div style={{ flex: 1, fontSize: '14px', color: isWarning ? '#7f1d1d' : '#475569', lineHeight: '1.6' }}>
                {typeof item === 'string' ? item : JSON.stringify(item, null, 2)}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  // Render confidence and risk score
  const renderScoreCard = () => {
    const confidence = getValue('Confidence_and_Risk_Score.Confidence') || getValue('Confidence_Score');
    const riskLevel = getValue('Confidence_and_Risk_Score.Risk_Level') || getValue('Risk_Level');
    const documentClarity = getValue('Confidence_and_Risk_Score.Document_Clarity');
    const riskColor = getRiskColor(riskLevel);

    if (!confidence && !riskLevel) return null;

    return (
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px', marginBottom: '32px' }}>
        {confidence && (
          <div style={{ background: '#ffffff', borderRadius: '12px', padding: '20px', border: '1px solid #e5e7eb', textAlign: 'center' }}>
            <IonIcon icon={shieldCheckmarkOutline} style={{ fontSize: '32px', color: getCategoryInfo().color, marginBottom: '8px' }} />
            <div style={{ fontSize: '28px', fontWeight: 700, color: '#0f172a', marginBottom: '4px' }}>
              {confidence}{typeof confidence === 'number' ? '/5' : ''}
            </div>
            <div style={{ fontSize: '13px', color: '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>
              Confidence Score
            </div>
          </div>
        )}

        {riskLevel && (
          <div style={{ 
            background: '#ffffff', 
            borderRadius: '12px', 
            padding: '20px', 
            border: `1px solid ${riskColor.border}`,
            textAlign: 'center' 
          }}>
            <IonIcon icon={warningOutline} style={{ fontSize: '32px', color: riskColor.text, marginBottom: '8px' }} />
            <div style={{ fontSize: '20px', fontWeight: 700, color: riskColor.text, marginBottom: '4px' }}>
              {riskLevel}
            </div>
            <div style={{ fontSize: '13px', color: '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>
              Risk Level
            </div>
          </div>
        )}

        {documentClarity && (
          <div style={{ background: '#ffffff', borderRadius: '12px', padding: '20px', border: '1px solid #e5e7eb', textAlign: 'center' }}>
            <IonIcon icon={documentAttachOutline} style={{ fontSize: '32px', color: '#10b981', marginBottom: '8px' }} />
            <div style={{ fontSize: '20px', fontWeight: 700, color: '#0f172a', marginBottom: '4px' }}>
              {documentClarity}
            </div>
            <div style={{ fontSize: '13px', color: '#64748b', fontWeight: 600, textTransform: 'uppercase' }}>
              Document Clarity
            </div>
          </div>
        )}
      </div>
    );
  };

  // Render category-specific sections
  const renderCategorySpecificSections = () => {
    switch (currentCategory.toLowerCase()) {
      case 'student':
        return (
          <>
            {renderObject(summary.Key_Terms, 'Key Terms & Conditions', documentAttachOutline)}
            {renderObject(summary.Rights_and_Fairness, 'Rights & Fairness', shieldCheckmarkOutline)}
          </>
        );
        
      case 'citizen':
        return (
          <>
            {renderObject(summary.Key_Terms, 'Key Terms & Conditions', documentAttachOutline)}
            {renderObject(summary.Rights_and_Obligations || summary.Rights_and_Fairness, 'Rights & Obligations', shieldCheckmarkOutline)}
            {renderObject(summary.Validation_Status, 'Validation Status', checkmarkCircleOutline)}
          </>
        );
        
      case 'business':
        return (
          <>
            {renderList(summary.Clause_Insights || [], 'Clause Insights', listOutline)}
            {renderObject(summary.Key_Terms, 'Key Terms & Conditions', documentAttachOutline)}
            {renderList(summary.Applicable_Laws || [], 'Applicable Laws', scaleOutline)}
            {renderObject(summary.Risk_and_Compliance, 'Risk & Compliance Analysis', alertCircleOutline)}
          </>
        );
        
      default:
        return null;
    }
  };

  // Render applicable laws section
  const renderApplicableLaws = () => {
    const applicableLaws = getValue('Applicable_Laws_and_Acts') || getValue('Applicable_Laws');
    if (!shouldDisplay(applicableLaws)) return null;

    return (
      <div
        style={{
          background: '#ffffff',
          borderRadius: '16px',
          padding: '32px',
          border: '1px solid #e5e7eb',
          marginBottom: '24px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
          <IonIcon icon={scaleOutline} style={{ fontSize: '24px', color: getCategoryInfo().color }} />
          <h2 style={{ fontSize: '22px', fontWeight: 600, color: '#0f172a', margin: 0 }}>
            {Array.isArray(applicableLaws) ? 'Applicable Laws' : 'Applicable Laws & Acts'}
          </h2>
        </div>

        {Array.isArray(applicableLaws) ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {applicableLaws.map((law, index) => (
              <div
                key={index}
                style={{
                  padding: '16px',
                  background: '#f8fafc',
                  borderRadius: '8px',
                  border: '1px solid #e2e8f0'
                }}
              >
                <div style={{ fontSize: '14px', color: '#475569', lineHeight: '1.6' }}>
                  {law}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            {applicableLaws.Explicit_Acts && applicableLaws.Explicit_Acts.length > 0 && (
              <div>
                <h3 style={{ fontSize: '16px', fontWeight: 600, color: '#0f172a', marginBottom: '12px' }}>
                  Explicit Acts
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {applicableLaws.Explicit_Acts.map((act: any, index: number) => (
                    <div
                      key={index}
                      style={{
                        padding: '16px',
                        background: '#f8fafc',
                        borderRadius: '8px',
                        border: '1px solid #e2e8f0'
                      }}
                    >
                      <div style={{ fontSize: '14px', fontWeight: 600, color: '#0f172a', marginBottom: '6px' }}>
                        {act.Act || act}
                      </div>
                      {act.Relevance && (
                        <div style={{ fontSize: '13px', color: '#64748b', lineHeight: '1.6' }}>
                          {act.Relevance}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {applicableLaws.Implicit_Acts && applicableLaws.Implicit_Acts.length > 0 && (
              <div>
                <h3 style={{ fontSize: '16px', fontWeight: 600, color: '#0f172a', marginBottom: '12px' }}>
                  Implicit Acts
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {applicableLaws.Implicit_Acts.map((act: any, index: number) => (
                    <div
                      key={index}
                      style={{
                        padding: '16px',
                        background: '#fffbeb',
                        borderRadius: '8px',
                        border: '1px solid #fde68a'
                      }}
                    >
                      <div style={{ fontSize: '14px', fontWeight: 600, color: '#0f172a', marginBottom: '6px' }}>
                        {act.Act || act}
                      </div>
                      {act.Reason && (
                        <div style={{ fontSize: '13px', color: '#78350f', lineHeight: '1.6' }}>
                          <strong>Reason:</strong> {act.Reason}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  // Action Buttons Component
  const renderActionButtons = () => (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      gap: '20px',
      marginTop: '40px',
      marginBottom: '40px',
      flexWrap: 'wrap'
    }}>
      <IonButton
        color="medium"
        fill="outline"
        onClick={() => history.goBack()}
        style={{ '--border-radius': '12px', padding: '18px 24px' }}
      >
        <IonIcon icon={arrowBackOutline} slot="start" />
        Back to Analysis
      </IonButton>

      <IonButton
        color="primary"
        fill="solid"
        onClick={handleGenerateMindMap}
        disabled={isGeneratingMindMap}
        style={{ '--border-radius': '12px', padding: '18px 24px' }}
      >
        {isGeneratingMindMap ? (
          <>
            <IonSpinner name="crescent" slot="start" />
            Generating...
          </>
        ) : (
          <>
            <IonIcon icon={gitNetworkOutline} slot="start" />
            Generate Mind Map
          </>
        )}
      </IonButton>

      <IonButton
        color="success"
        fill="solid"
        onClick={handleVideoButtonClick}
        disabled={isGeneratingVideo}
        style={{ '--border-radius': '12px', padding: '18px 24px' }}
      >
        {isGeneratingVideo ? (
          <>
            <IonSpinner name="crescent" slot="start" />
            Generating...
          </>
        ) : (
          <>
            <IonIcon icon={videocamOutline} slot="start" />
            Generate Video
          </>
        )}
      </IonButton>
    </div>
  );

  return (
    <IonPage>
      <IonContent fullscreen style={{ background: '#f8fafc' }}>
        {/* Navigation */}
        <nav
          style={{
            background: '#ffffff',
            padding: '22px 48px',
            borderBottom: '1px solid #e5e7eb',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px', height: '40px' }}>
            <IonIcon icon={documentTextOutline} style={{ fontSize: '26px', color: '#2563eb' }} />
            <span style={{ fontSize: '22px', fontWeight: 600, color: '#0f172a' }}>
              LexiNote
            </span>
          </div>
          
          <div style={{ textAlign: 'center' }}>
            <span
              style={{
                display: 'inline-block',
                padding: '8px 16px',
                background: '#eff6ff',
                color: getCategoryInfo().color,
                borderRadius: '20px',
                fontSize: '14px',
                fontWeight: 600
              }}
            >
              {currentCategory} Document
            </span>
          </div>
        </nav>

        <section style={{ padding: '40px 48px' }}>
          <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
            
            {/* Quick Stats Cards */}
            {renderScoreCard()}

            {/* Simple Summary */}
            {shouldDisplay(summary.Simple_Summary) && (
              <div
                style={{
                  background: 'linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)',
                  borderRadius: '16px',
                  padding: '32px',
                  border: '2px solid #93c5fd',
                  marginBottom: '32px'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
                  <IonIcon icon={bulbOutline} style={{ fontSize: '28px', color: getCategoryInfo().color }} />
                  <h2 style={{ fontSize: '22px', fontWeight: 600, color: '#1e40af', margin: 0 }}>
                    Quick Summary
                  </h2>
                </div>
                <p style={{ fontSize: '16px', color: '#1e3a8a', lineHeight: '1.8', margin: 0 }}>
                  {summary.Simple_Summary}
                </p>
              </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px', marginBottom: '32px' }}>
              
              {/* Left Column - Main Content */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                
                {/* Document Header */}
                {renderObject(summary.Header, 'Document Details', documentTextOutline)}

                {/* Overview */}
                {shouldDisplay(summary.Overview) && (
                  <div
                    style={{
                      background: '#ffffff',
                      borderRadius: '16px',
                      padding: '32px',
                      border: '1px solid #e5e7eb'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
                      <IonIcon icon={listOutline} style={{ fontSize: '24px', color: getCategoryInfo().color }} />
                      <h2 style={{ fontSize: '22px', fontWeight: 600, color: '#0f172a', margin: 0 }}>
                        Overview
                      </h2>
                    </div>
                    <p style={{ fontSize: '15px', color: '#475569', lineHeight: '1.8', margin: 0 }}>
                      {summary.Overview}
                    </p>
                  </div>
                )}

                {/* Parties Involved */}
                {renderObject(summary.Parties_Involved, 'Parties Involved', peopleOutline)}

                {/* Category Specific Sections */}
                {renderCategorySpecificSections()}
              </div>

              {/* Right Column - Sidebar */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                
                {/* Recommendations */}
                {renderList(summary.Recommendations || [], 'Recommendations', trophyOutline)}

                {/* Risk and Compliance */}
                {renderList(summary.Risk_and_Compliance || [], 'Risk & Compliance Issues', alertCircleOutline, true)}
              </div>
            </div>

            {/* Applicable Laws */}
            {renderApplicableLaws()}

            {/* Action Buttons */}
            {renderActionButtons()}

            {/* Original Text Reference */}
            {extractedText && (
              <div
                style={{
                  background: '#ffffff',
                  borderRadius: '16px',
                  padding: '32px',
                  border: '1px solid #e5e7eb',
                  marginBottom: '32px'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                  <IonIcon icon={documentTextOutline} style={{ fontSize: '20px', color: getCategoryInfo().color }} />
                  <h2 style={{ fontSize: '22px', fontWeight: 600, color: '#0f172a', margin: 0 }}>
                    Original Text Reference
                  </h2>
                </div>
                <div style={{
                  maxHeight: '300px',
                  overflowY: 'auto',
                  padding: '20px',
                  background: '#f8fafc',
                  borderRadius: '8px',
                  border: '1px solid #e2e8f0',
                  fontSize: '14px',
                  color: '#475569',
                  lineHeight: '1.6',
                  whiteSpace: 'pre-wrap'
                }}>
                  {extractedText}
                </div>
              </div>
            )}
          </div>
        </section>

        {/* ============== MODALS ============== */}

        {/* Language Selector Modal */}
        <IonModal isOpen={showLanguageSelector} onDidDismiss={() => setShowLanguageSelector(false)}>
          <IonHeader>
            <IonToolbar>
              <IonTitle>Select Language for Video</IonTitle>
              <IonButtons slot="end">
                <IonButton onClick={() => setShowLanguageSelector(false)}>
                  <IonIcon icon={closeOutline} />
                </IonButton>
              </IonButtons>
            </IonToolbar>
          </IonHeader>
          <IonContent style={{ padding: '20px' }}>
            <div style={{ textAlign: 'center', padding: '40px 20px' }}>
              <IonIcon icon={sparklesOutline} style={{ fontSize: '64px', color: '#3b82f6', marginBottom: '20px' }} />
              <h2 style={{ fontSize: '24px', fontWeight: 600, color: '#0f172a', marginBottom: '10px' }}>
                Choose Video Language
              </h2>
              <p style={{ color: '#64748b', marginBottom: '30px' }}>
                Select the language for the AI-generated video explanation
              </p>
              
              <div style={{ maxWidth: '400px', margin: '0 auto', marginBottom: '30px' }}>
                <IonSelect
                  value={selectedLanguage}
                  onIonChange={(e) => setSelectedLanguage(e.detail.value)}
                  interface="popover"
                  style={{ width: '100%' }}
                >
                  <IonSelectOption value="en">English</IonSelectOption>
                  <IonSelectOption value="hi">Hindi</IonSelectOption>
                  <IonSelectOption value="ta">Tamil</IonSelectOption>
                  <IonSelectOption value="te">Telugu</IonSelectOption>
                  <IonSelectOption value="kn">Kannada</IonSelectOption>
                  <IonSelectOption value="ml">Malayalam</IonSelectOption>
                  <IonSelectOption value="bn">Bengali</IonSelectOption>
                  <IonSelectOption value="gu">Gujarati</IonSelectOption>
                </IonSelect>
              </div>

              <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
                <IonButton
                  color="medium"
                  fill="outline"
                  onClick={() => setShowLanguageSelector(false)}
                >
                  Cancel
                </IonButton>
                <IonButton
                  color="primary"
                  onClick={() => handleGenerateVideo(selectedLanguage)}
                >
                  Generate Video
                </IonButton>
              </div>
            </div>
          </IonContent>
        </IonModal>

        {/* Mind Map Modal */}
        <IonModal 
          isOpen={showMindMapModal} 
          onDidDismiss={() => setShowMindMapModal(false)}
          cssClass="fullscreen-modal"
        >
          <IonHeader>
            <IonToolbar>
              <IonTitle>Mind Map Visualization</IonTitle>
              <IonButtons slot="end">
                <IonButton onClick={() => setShowMindMapModal(false)}>
                  <IonIcon icon={closeOutline} />
                </IonButton>
              </IonButtons>
            </IonToolbar>
          </IonHeader>
          <IonContent>
            {mindMapError ? (
              <div style={{ textAlign: 'center', padding: '40px 20px' }}>
                <IonIcon icon={warningOutline} style={{ fontSize: '64px', color: '#ef4444', marginBottom: '20px' }} />
                <h2 style={{ fontSize: '24px', fontWeight: 600, color: '#0f172a', marginBottom: '10px' }}>
                  Error Generating Mind Map
                </h2>
                <p style={{ color: '#64748b', marginBottom: '30px' }}>
                  {mindMapError}
                </p>
                <IonButton onClick={handleGenerateMindMap}>
                  Try Again
                </IonButton>
              </div>
            ) : mindMapData ? (
              <div style={{ height: 'calc(100vh - 56px)', position: 'relative' }}>
                {reactFlowNodes.length > 0 ? (
                  <ReactFlow
                    nodes={reactFlowNodes}
                    edges={reactFlowEdges}
                    fitView
                    style={{ background: '#f8fafc' }}
                  >
                    <Controls />
                    <Background color="#ccc" gap={16} />
                    <MiniMap />
                  </ReactFlow>
                ) : (
                  // Fallback tree view if React Flow not working
                  <div style={{ padding: '40px', overflowY: 'auto', maxHeight: 'calc(100vh - 100px)' }}>
                    {(() => {
                      const renderNode = (node: MindMapNode, level: number = 0) => {
                        const statusColors: any = {
                          positive: '#10b981',
                          negative: '#ef4444',
                          neutral: '#64748b',
                          info: '#3b82f6'
                        };

                        const bgColors: any = {
                          positive: '#f0fdf4',
                          negative: '#fef2f2',
                          neutral: '#f8fafc',
                          info: '#eff6ff'
                        };

                        return (
                          <div key={node.id} style={{ marginLeft: level * 40 + 'px', marginBottom: '16px' }}>
                            <div
                              style={{
                                background: bgColors[node.status] || '#ffffff',
                                border: `2px solid ${statusColors[node.status] || '#e5e7eb'}`,
                                borderRadius: '12px',
                                padding: '16px',
                                display: 'inline-block',
                                minWidth: '250px',
                                cursor: 'pointer',
                                transition: 'all 0.2s'
                              }}
                            >
                              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                                <div style={{ fontSize: '20px' }}>
                                  {node.icon === 'document' && '📄'}
                                  {node.icon === 'law' && '⚖️'}
                                  {node.icon === 'people' && '👥'}
                                  {node.icon === 'risk_high' && '⚠️'}
                                  {node.icon === 'risk_low' && '✅'}
                                  {node.icon === 'check' && '✓'}
                                  {node.icon === 'money' && '💰'}
                                  {node.icon === 'time' && '⏰'}
                                  {node.icon === 'info' && 'ℹ️'}
                                  {node.icon === 'recommendation' && '💡'}
                                  {node.icon === 'star' && '⭐'}
                                </div>
                                <div>
                                  <div style={{ fontWeight: 700, fontSize: '16px', color: '#0f172a' }}>
                                    {node.label}
                                  </div>
                                  {node.secondaryLabel && (
                                    <div style={{ fontSize: '12px', color: statusColors[node.status] || '#64748b', fontWeight: 600 }}>
                                      {node.secondaryLabel}
                                    </div>
                                  )}
                                </div>
                              </div>
                              {node.details && node.details !== 'N/A' && (
                                <div style={{ fontSize: '13px', color: '#64748b', lineHeight: '1.5' }}>
                                  {node.details}
                                </div>
                              )}
                            </div>
                            {node.children && node.children.length > 0 && (
                              <div style={{ marginTop: '12px' }}>
                                {node.children.map((child: any) => renderNode(child, level + 1))}
                              </div>
                            )}
                          </div>
                        );
                      };

                      return renderNode(mindMapData);
                    })()}
                  </div>
                )}
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '40px 20px' }}>
                <IonSpinner name="crescent" style={{ width: '60px', height: '60px', marginBottom: '20px' }} />
                <p>Loading mind map...</p>
              </div>
            )}
          </IonContent>
        </IonModal>

        {/* Video Modal */}
        <IonModal 
          isOpen={showVideoModal} 
          onDidDismiss={() => setShowVideoModal(false)}
          cssClass="fullscreen-modal"
        >
          <IonHeader>
            <IonToolbar>
              <IonTitle>AI-Generated Video Explanation</IonTitle>
              <IonButtons slot="end">
                <IonButton onClick={() => setShowVideoModal(false)}>
                  <IonIcon icon={closeOutline} />
                </IonButton>
              </IonButtons>
            </IonToolbar>
          </IonHeader>
          <IonContent>
            {videoError ? (
              <div style={{ textAlign: 'center', padding: '40px 20px' }}>
                <IonIcon icon={warningOutline} style={{ fontSize: '64px', color: '#ef4444', marginBottom: '20px' }} />
                <h2 style={{ fontSize: '24px', fontWeight: 600, color: '#0f172a', marginBottom: '10px' }}>
                  Error Generating Video
                </h2>
                <p style={{ color: '#64748b', marginBottom: '30px' }}>
                  {videoError}
                </p>
                <IonButton onClick={() => handleGenerateVideo(selectedLanguage)}>
                  Try Again
                </IonButton>
              </div>
            ) : videoUrl ? (
              <div style={{ textAlign: 'center', padding: '40px 20px' }}>
                <div style={{ maxWidth: '800px', margin: '0 auto' }}>
                  <h2 style={{ fontSize: '24px', fontWeight: 600, color: '#0f172a', marginBottom: '30px' }}>
                    Video Explanation ({selectedLanguage.toUpperCase()})
                  </h2>
                  
                  <div style={{
                    background: '#000',
                    borderRadius: '12px',
                    overflow: 'hidden',
                    marginBottom: '30px',
                    boxShadow: '0 10px 25px rgba(0,0,0,0.1)'
                  }}>
                    <video
                      controls
                      style={{ width: '100%', height: 'auto', maxHeight: '70vh' }}
                      src={videoUrl}
                    >
                      Your browser does not support the video tag.
                    </video>
                  </div>

                  <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
                    <IonButton
                      color="primary"
                      onClick={() => {
                        const link = document.createElement('a');
                        link.href = videoUrl;
                        link.download = `document-summary-${currentCategory}-${new Date().getTime()}.mp4`;
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);
                      }}
                    >
                      <IonIcon icon={downloadOutline} slot="start" />
                      Download Video
                    </IonButton>
                    <IonButton
                      color="medium"
                      fill="outline"
                      onClick={() => setShowVideoModal(false)}
                    >
                      Close
                    </IonButton>
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '40px 20px' }}>
                <IonSpinner name="crescent" style={{ width: '60px', height: '60px', marginBottom: '20px' }} />
                <p>Generating video...</p>
              </div>
            )}
          </IonContent>
        </IonModal>

      </IonContent>
    </IonPage>
  );
};

export default SummaryPage;