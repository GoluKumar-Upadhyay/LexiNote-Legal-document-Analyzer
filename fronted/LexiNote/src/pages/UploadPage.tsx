import React, { useState } from 'react';
import {
  IonContent,
  IonPage,
  IonIcon,
  IonButton,
  IonSpinner
} from '@ionic/react';
import {
  documentTextOutline,
  cloudUploadOutline,
  arrowBackOutline,
  checkmarkCircleOutline,
  closeCircleOutline,
  shieldCheckmarkOutline,
  alertCircleOutline,
  informationCircleOutline,
  sparklesOutline
} from 'ionicons/icons';
import { useHistory, useParams } from 'react-router-dom';

interface RouteParams {
  category: string;
}

interface AnalysisResult {
  confidence: string;
  extracted_text: string;
  predicted_category: string;
  reason: string;
  suggested_action: string;
}

const UploadPage: React.FC = () => {
  const history = useHistory();
  const { category } = useParams<RouteParams>();
  
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [uploadError, setUploadError] = useState<string>('');
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [generatingSummary, setGeneratingSummary] = useState(false);

  // Get category display name
  const getCategoryDisplay = (cat: string) => {
    const categories: { [key: string]: string } = {
      citizen: 'citizen',
      business: 'Business Professional',
      student: 'Student',
      CITIZEN_DOC: 'Citizen Document',
      BUSINESS_DOC: 'Business Document',
      STUDENT_DOC: 'Student Document'
    };
    return categories[cat] || cat;
  };

  // Get confidence badge color
  const getConfidenceBadge = (confidence: string) => {
    const colors = {
      high: { bg: '#f0fdf4', border: '#86efac', text: '#16a34a' },
      medium: { bg: '#fef3c7', border: '#fcd34d', text: '#ca8a04' },
      low: { bg: '#fef2f2', border: '#fca5a5', text: '#dc2626' }
    };
    return colors[confidence.toLowerCase() as keyof typeof colors] || colors.medium;
  };

  // Handle file selection
  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setUploadSuccess(false);
      setUploadError('');
      setAnalysisResult(null);
    }
  };

  // Handle file upload
  const handleUpload = async () => {
    if (!selectedFile) {
      setUploadError('Please select a file first');
      return;
    }

    setUploading(true);
    setUploadError('');
    setUploadSuccess(false);
    setAnalysisResult(null);

    try {
      // Create FormData
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('category', category);

      // Send to backend
      const response = await fetch('http://localhost:8080/uploads', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      const result: AnalysisResult = await response.json();
      console.log('Upload successful:', result);
      
      setUploadSuccess(true);
      setAnalysisResult(result);
      setSelectedFile(null);
      
      // Reset file input
      const fileInput = document.getElementById('fileInput') as HTMLInputElement;
      if (fileInput) fileInput.value = '';

    } catch (error) {
      console.error('Upload error:', error);
      setUploadError(error instanceof Error ? error.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  // Handle generate summary
  const handleGenerateSummary = async () => {
    if (!analysisResult?.extracted_text) return;

    setGeneratingSummary(true);

    try {
      // Create form data for x-www-form-urlencoded
      const formData = new URLSearchParams();
      formData.append('category', category);
      formData.append('document_text', analysisResult.extracted_text);

      const response = await fetch('http://localhost:5001/summarize', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData.toString()
      });

      if (!response.ok) {
        throw new Error(`Summary generation failed: ${response.statusText}`);
      }

      const summaryData = await response.json();
      
      // Navigate to summary page with data
      history.push({
        pathname: '/summary',
        state: { 
          summaryData,
          extractedText: analysisResult.extracted_text,
          documentType: analysisResult.predicted_category,
          category: category
        }
      });

    } catch (error) {
      console.error('Summary generation error:', error);
      alert('Failed to generate summary. Please try again.');
    } finally {
      setGeneratingSummary(false);
    }
  };

  // Handle new upload
  const handleNewUpload = () => {
    setAnalysisResult(null);
    setUploadSuccess(false);
    setUploadError('');
  };

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
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <IonIcon icon={documentTextOutline} style={{ fontSize: '26px', color: '#2563eb' }} />
            <span style={{ fontSize: '22px', fontWeight: 600, color: '#0f172a' }}>
              LexiNote
            </span>
          </div>
          
          <div style={{ textAlign: 'center', marginBottom: '32px' }}>
            <span
              style={{
                display: 'inline-block',
                padding: '8px 16px',
                background: '#eff6ff',
                color: '#2563eb',
                borderRadius: '20px',
                fontSize: '14px',
                fontWeight: 600,
              }}
            >
              {getCategoryDisplay(category)}
            </span>
          </div>
        </nav>

        <section style={{ padding: '40px 48px' }}>
          <div style={{ maxWidth: analysisResult ? '100%' : '900px', margin: '0 auto' }}>
            
            {/* Show Upload Card or Results */}
            {!analysisResult ? (
              /* Upload Card */
              <div
                style={{
                  background: '#ffffff',
                  borderRadius: '16px',
                  border: '2px dashed #e5e7eb',
                  padding: '48px',
                  textAlign: 'center'
                }}
              >
                <div
                  style={{
                    width: '72px',
                    height: '72px',
                    borderRadius: '50%',
                    background: '#f1f5f9',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    margin: '0 auto 24px'
                  }}
                >
                  <IonIcon
                    icon={cloudUploadOutline}
                    style={{ fontSize: '36px', color: '#2563eb' }}
                  />
                </div>

                <h2 style={{ fontSize: '24px', fontWeight: 600, color: '#0f172a', marginBottom: '12px' }}>
                  Upload Your Document
                </h2>
                <p style={{ fontSize: '15px', color: '#64748b', marginBottom: '32px' }}>
                  Select a legal document to analyze (PDF, DOC, DOCX, Png, Jpg)
                </p>

                <input
                  id="fileInput"
                  type="file"
                  accept=".pdf,.doc,.docx"
                  onChange={handleFileChange}
                  style={{ display: 'none' }}
                />

                <label
                  htmlFor="fileInput"
                  style={{
                    display: 'inline-block',
                    padding: '12px 24px',
                    background: '#f1f5f9',
                    color: '#0f172a',
                    borderRadius: '8px',
                    fontSize: '15px',
                    fontWeight: 500,
                    cursor: 'pointer',
                    marginBottom: '24px',
                    transition: 'background 0.2s'
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = '#e2e8f0')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = '#f1f5f9')}
                >
                  Choose File
                </label>

                {selectedFile && (
                  <div
                    style={{
                      background: '#f8fafc',
                      borderRadius: '8px',
                      padding: '16px',
                      marginBottom: '24px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '12px'
                    }}
                  >
                    <IonIcon icon={documentTextOutline} style={{ fontSize: '20px', color: '#2563eb' }} />
                    <span style={{ fontSize: '14px', color: '#0f172a', fontWeight: 500 }}>
                      {selectedFile.name}
                    </span>
                    <span style={{ fontSize: '13px', color: '#64748b' }}>
                      ({(selectedFile.size / 1024).toFixed(2)} KB)
                    </span>
                  </div>
                )}

                <IonButton
                  onClick={handleUpload}
                  disabled={!selectedFile || uploading}
                  style={{
                    '--background': '#2563eb',
                    '--background-hover': '#1d4ed8',
                    '--border-radius': '8px',
                    '--padding-start': '32px',
                    '--padding-end': '32px',
                    fontSize: '15px',
                    fontWeight: 600,
                    height: '48px'
                  }}
                >
                  {uploading ? (
                    <>
                      <IonSpinner name="crescent" style={{ marginRight: '8px' }} />
                      Uploading...
                    </>
                  ) : (
                    'Upload & Analyze'
                  )}
                </IonButton>

                {uploadError && (
                  <div
                    style={{
                      marginTop: '24px',
                      padding: '16px',
                      background: '#fef2f2',
                      border: '1px solid #fca5a5',
                      borderRadius: '8px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '12px'
                    }}
                  >
                    <IonIcon icon={closeCircleOutline} style={{ fontSize: '20px', color: '#dc2626' }} />
                    <span style={{ fontSize: '14px', color: '#dc2626', fontWeight: 500 }}>
                      {uploadError}
                    </span>
                  </div>
                )}
              </div>
            ) : (
              /* Analysis Results Card */
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '24px', alignItems: 'start' }}>
                
                {/* Left Column - Summary Cards */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                  
                  {/* Success Header */}
                  <div
                    style={{
                      background: '#ffffff',
                      borderRadius: '16px',
                      padding: '32px',
                      border: '1px solid #e5e7eb',
                      textAlign: 'center'
                    }}
                  >
                    <div
                      style={{
                        width: '56px',
                        height: '56px',
                        borderRadius: '50%',
                        background: '#f0fdf4',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        margin: '0 auto 16px'
                      }}
                    >
                      <IonIcon icon={checkmarkCircleOutline} style={{ fontSize: '32px', color: '#16a34a' }} />
                    </div>
                    <h2 style={{ fontSize: '24px', fontWeight: 600, color: '#0f172a', marginBottom: '8px' }}>
                      Analysis Complete!
                    </h2>
                    <p style={{ fontSize: '15px', color: '#64748b' }}>
                      Your document has been successfully analyzed
                    </p>
                  </div>

                  {/* Analysis Summary Card */}
                  <div
                    style={{
                      background: '#ffffff',
                      borderRadius: '16px',
                      padding: '24px',
                      border: '1px solid #e5e7eb'
                    }}
                  >
                    <h3 style={{ fontSize: '18px', fontWeight: 600, color: '#0f172a', marginBottom: '20px' }}>
                      Analysis Summary
                    </h3>

                    {/* Confidence Level */}
                    <div style={{ marginBottom: '20px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                        <IonIcon icon={shieldCheckmarkOutline} style={{ fontSize: '18px', color: '#64748b' }} />
                        <span style={{ fontSize: '13px', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                          Confidence Level
                        </span>
                      </div>
                      <span
                        style={{
                          display: 'inline-block',
                          padding: '6px 12px',
                          background: getConfidenceBadge(analysisResult.confidence).bg,
                          border: `1px solid ${getConfidenceBadge(analysisResult.confidence).border}`,
                          color: getConfidenceBadge(analysisResult.confidence).text,
                          borderRadius: '6px',
                          fontSize: '13px',
                          fontWeight: 600,
                          textTransform: 'uppercase'
                        }}
                      >
                        {analysisResult.confidence}
                      </span>
                    </div>

                    {/* Predicted Category */}
                    <div style={{ marginBottom: '20px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                        <IonIcon icon={documentTextOutline} style={{ fontSize: '18px', color: '#64748b' }} />
                        <span style={{ fontSize: '13px', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                          Document Type
                        </span>
                      </div>
                      <p style={{ fontSize: '15px', color: '#0f172a', fontWeight: 500 }}>
                        {getCategoryDisplay(analysisResult.predicted_category)}
                      </p>
                    </div>

                    {/* Suggested Action */}
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                        <IonIcon icon={alertCircleOutline} style={{ fontSize: '18px', color: '#64748b' }} />
                        <span style={{ fontSize: '13px', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                          Recommended Action
                        </span>
                      </div>
                      <p style={{ fontSize: '14px', color: '#475569' }}>
                        {analysisResult.suggested_action}
                      </p>
                    </div>
                  </div>

                  {/* Action Button */}
                  <IonButton
                    onClick={handleNewUpload}
                    expand="block"
                    style={{
                      '--background': '#2563eb',
                      '--background-hover': '#1d4ed8',
                      '--border-radius': '12px',
                      fontSize: '15px',
                      fontWeight: 600,
                      height: '48px'
                    }}
                  >
                    Upload Another Document
                  </IonButton>
                </div>

                {/* Right Column - Detailed Analysis */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                  
                  {/* Analysis Details */}
                  <div
                    style={{
                      background: '#ffffff',
                      borderRadius: '16px',
                      padding: '32px',
                      border: '1px solid #e5e7eb'
                    }}
                  >
                    <h3 style={{ fontSize: '18px', fontWeight: 600, color: '#0f172a', marginBottom: '16px' }}>
                      Detailed Analysis
                    </h3>

                    {/* Reason */}
                    <div style={{ marginBottom: '24px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                        <IonIcon icon={informationCircleOutline} style={{ fontSize: '18px', color: '#64748b' }} />
                        <span style={{ fontSize: '13px', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                          Why This Classification?
                        </span>
                      </div>
                      <p style={{ fontSize: '14px', color: '#475569', lineHeight: '1.7' }}>
                        {analysisResult.reason}
                      </p>
                    </div>
                  </div>

                  {/* Extracted Text - With Summary Button */}
                  <div
                    style={{
                      background: '#ffffff',
                      borderRadius: '16px',
                      padding: '32px',
                      border: '1px solid #e5e7eb',
                      position: 'relative'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <IonIcon icon={documentTextOutline} style={{ fontSize: '18px', color: '#64748b' }} />
                        <span style={{ fontSize: '13px', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                          Extracted Text
                        </span>
                      </div>
                      
                      {/* Generate Summary Button */}
                      <button
                        onClick={handleGenerateSummary}
                        disabled={generatingSummary}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '8px',
                          padding: '8px 16px',
                          background: generatingSummary ? '#e2e8f0' : '#8b5cf6',
                          color: '#ffffff',
                          border: 'none',
                          borderRadius: '8px',
                          fontSize: '13px',
                          fontWeight: 600,
                          cursor: generatingSummary ? 'not-allowed' : 'pointer',
                          transition: 'all 0.2s',
                          opacity: generatingSummary ? 0.7 : 1
                        }}
                        onMouseEnter={(e) => {
                          if (!generatingSummary) {
                            e.currentTarget.style.background = '#7c3aed';
                            e.currentTarget.style.transform = 'translateY(-1px)';
                          }
                        }}
                        onMouseLeave={(e) => {
                          if (!generatingSummary) {
                            e.currentTarget.style.background = '#8b5cf6';
                            e.currentTarget.style.transform = 'translateY(0)';
                          }
                        }}
                      >
                        {generatingSummary ? (
                          <>
                            <IonSpinner name="crescent" style={{ width: '16px', height: '16px' }} />
                            Generating...
                          </>
                        ) : (
                          <>
                            <IonIcon icon={sparklesOutline} style={{ fontSize: '16px' }} />
                            Generate Summary
                          </>
                        )}
                      </button>
                    </div>
                    
                    <div
                      style={{
                        background: '#f8fafc',
                        borderRadius: '8px',
                        padding: '20px',
                        maxHeight: '600px',
                        overflowY: 'auto',
                        fontSize: '13px',
                        color: '#475569',
                        lineHeight: '1.8',
                        whiteSpace: 'pre-wrap',
                        fontFamily: 'ui-monospace, monospace',
                        border: '1px solid #e2e8f0'
                      }}
                    >
                      {analysisResult.extracted_text}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Info Section */}
            {!analysisResult && (
              <div style={{ marginTop: '32px', textAlign: 'center' }}>
                <p style={{ fontSize: '14px', color: '#64748b', lineHeight: '1.6' }}>
                  Your document will be analyzed using AI to extract key insights,
                  legal terms, and provide simplified explanations based on Indian law.
                </p>
              </div>
            )}
          </div>
        </section>
      </IonContent>
    </IonPage>
  );
};

export default UploadPage;