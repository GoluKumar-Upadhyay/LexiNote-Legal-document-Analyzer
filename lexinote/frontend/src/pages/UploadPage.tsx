import React, { useEffect, useMemo, useState } from 'react';
import { IonButton, IonContent, IonIcon, IonPage, IonSpinner } from '@ionic/react';
import {
  alertCircleOutline,
  arrowBackOutline,
  checkmarkCircleOutline,
  cloudUploadOutline,
  closeCircleOutline,
  documentTextOutline,
  informationCircleOutline,
  shieldCheckmarkOutline,
  sparklesOutline,
  warningOutline,
} from 'ionicons/icons';
import { useHistory, useParams } from 'react-router-dom';
import { buildApiUrl } from '../config/api';
import { CATEGORY_CONFIG, CategoryKey } from '../data/categories';

interface RouteParams {
  category: CategoryKey;
}

interface AnalysisResult {
  confidence: string;
  extracted_text: string;
  predicted_category: string;
  reason: string;
  suggested_action: string;
  can_generate_summary?: boolean;
  expected_documents?: string[];
  _meta?: {
    provider_used?: string;
    warnings?: string[];
  };
}

const UploadPage: React.FC = () => {
  const history = useHistory();
  const { category } = useParams<RouteParams>();
  const config = CATEGORY_CONFIG[category] || CATEGORY_CONFIG.citizen;
  const uploadStateKey = `lexinote-upload-${category}`;

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [generatingSummary, setGeneratingSummary] = useState(false);

  const isMismatched = useMemo(() => {
    if (!analysisResult?.predicted_category) return false;
    return analysisResult.predicted_category !== `${category.toUpperCase()}_DOC`;
  }, [analysisResult, category]);

  useEffect(() => {
    try {
      const saved = sessionStorage.getItem(uploadStateKey);
      if (!saved) return;
      const parsed = JSON.parse(saved) as AnalysisResult;
      setAnalysisResult(parsed);
    } catch {
      sessionStorage.removeItem(uploadStateKey);
    }
  }, [uploadStateKey]);

  useEffect(() => {
    if (!analysisResult) return;
    sessionStorage.setItem(uploadStateKey, JSON.stringify(analysisResult));
  }, [analysisResult, uploadStateKey]);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] || null;
    setSelectedFile(file);
    setUploadError('');
    if (file) {
      setAnalysisResult(null);
      sessionStorage.removeItem(uploadStateKey);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setUploadError('Please choose a file before uploading.');
      return;
    }

    setUploading(true);
    setUploadError('');
    setAnalysisResult(null);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('category', category);

      const response = await fetch(buildApiUrl('/uploads'), {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || `Upload failed with status ${response.status}`);
      }

      const result: AnalysisResult = await response.json();
      setAnalysisResult(result);
      setSelectedFile(null);
      const fileInput = document.getElementById('fileInput') as HTMLInputElement | null;
      if (fileInput) fileInput.value = '';
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleGenerateSummary = async () => {
    if (!analysisResult?.extracted_text || analysisResult.can_generate_summary === false) {
      return;
    }

    setGeneratingSummary(true);
    try {
      const formData = new URLSearchParams();
      formData.append('category', category);
      formData.append('document_text', analysisResult.extracted_text);

      const response = await fetch(buildApiUrl('/summarize'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData.toString(),
      });

      if (!response.ok) {
        throw new Error(`Summary generation failed: ${response.statusText}`);
      }

      const summaryData = await response.json();
      history.push({
        pathname: '/summary',
        state: {
          summaryData,
          extractedText: analysisResult.extracted_text,
          documentType: analysisResult.predicted_category,
          category,
          backPath: `/upload/${category}`,
        },
      });
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : 'Summary generation failed');
    } finally {
      setGeneratingSummary(false);
    }
  };

  return (
    <IonPage>
      <IonContent fullscreen>
        <div style={{ minHeight: '100vh', background: '#f5f7f4' }}>
          <div style={{ height: '7px', background: 'linear-gradient(90deg, #ff9933 0%, #ffffff 50%, #138808 100%)' }} />

          <nav style={{ background: '#ffffff', borderBottom: '1px solid #d4dfe8', padding: '18px 30px' }}>
            <div
              style={{
                maxWidth: '1240px',
                margin: '0 auto',
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
                    width: '50px',
                    height: '50px',
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
                  <div style={{ fontSize: '13px', textTransform: 'uppercase', letterSpacing: '0.12em', color: '#6a7a89' }}>
                    {config.department}
                  </div>
                  <div style={{ fontWeight: 700, color: '#102235', fontSize: '24px' }}>{config.title}</div>
                </div>
              </div>

              <IonButton
                fill="outline"
                onClick={() => history.push('/features')}
                style={{ '--border-radius': '14px', '--border-color': '#c2ced9', '--color': '#102235' }}
              >
                <IonIcon icon={arrowBackOutline} slot="start" />
                Change Section
              </IonButton>
            </div>
          </nav>

          <section style={{ maxWidth: '1240px', margin: '0 auto', padding: '28px 24px 80px' }}>
            <div
              style={{
                background: '#ffffff',
                borderRadius: '26px',
                border: '1px solid #d4dfe8',
                padding: '22px 24px',
                marginBottom: '24px',
              }}
            >
              <h1 style={{ fontSize: 'clamp(2rem, 3.8vw, 3.4rem)', color: '#102235', marginBottom: '10px' }}>{config.uploadTitle}</h1>
              <p style={{ color: '#48576a', fontSize: '17px', lineHeight: 1.8, maxWidth: '900px' }}>{config.uploadHint}</p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(300px, 370px) minmax(0, 1fr)', gap: '24px', alignItems: 'start' }}>
              <aside
                style={{
                  background: '#ffffff',
                  border: '1px solid #d4dfe8',
                  borderRadius: '24px',
                  padding: '22px',
                  boxShadow: '0 18px 40px rgba(16, 34, 53, 0.05)',
                }}
              >
                <div
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '8px 12px',
                    borderRadius: '999px',
                    background: `${config.accent}14`,
                    color: config.accent,
                    fontWeight: 700,
                    fontSize: '12px',
                    marginBottom: '16px',
                  }}
                >
                  <IonIcon icon={shieldCheckmarkOutline} />
                  Mandatory upload rules
                </div>

                <div
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '10px',
                    padding: '14px 16px',
                    borderRadius: '18px',
                    background: '#fff7ef',
                    color: '#8a3b12',
                    marginBottom: '18px',
                  }}
                >
                  <IonIcon icon={warningOutline} style={{ marginTop: '2px', fontSize: '18px' }} />
                  <span style={{ lineHeight: 1.65, fontSize: '14px', fontWeight: 600 }}>{config.warning}</span>
                </div>

                <div style={{ display: 'grid', gap: '10px', marginBottom: '18px' }}>
                  {config.supportedDocs.map((doc) => (
                    <div
                      key={doc}
                      style={{
                        display: 'flex',
                        gap: '10px',
                        alignItems: 'center',
                        padding: '12px 14px',
                        borderRadius: '15px',
                        background: config.surface,
                      }}
                    >
                      <IonIcon icon={checkmarkCircleOutline} style={{ fontSize: '18px', color: config.accent }} />
                      <span style={{ color: '#36485a', fontSize: '14px' }}>{doc}</span>
                    </div>
                  ))}
                </div>

                <div
                  style={{
                    borderRadius: '18px',
                    border: '1px solid #d4dfe8',
                    background: '#f7fafc',
                    padding: '16px',
                    color: '#48576a',
                    fontSize: '14px',
                    lineHeight: 1.7,
                  }}
                >
                  Uploading the correct document type gives better clause extraction, better risk analysis, and fewer false warnings.
                </div>
              </aside>

              <div style={{ display: 'grid', gap: '20px' }}>
                {!analysisResult ? (
                  <div
                    style={{
                      background: '#ffffff',
                      borderRadius: '26px',
                      border: '1px solid #d4dfe8',
                      padding: '34px',
                      boxShadow: '0 18px 40px rgba(16, 34, 53, 0.05)',
                    }}
                  >
                    <div
                      style={{
                        width: '80px',
                        height: '80px',
                        borderRadius: '24px',
                        background: `${config.accent}14`,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        marginBottom: '22px',
                      }}
                    >
                      <IonIcon icon={cloudUploadOutline} style={{ color: config.accent, fontSize: '38px' }} />
                    </div>

                    <h2 style={{ fontSize: '34px', color: '#102235', marginBottom: '10px' }}>Upload and validate document</h2>
                    <p style={{ color: '#48576a', lineHeight: 1.8, marginBottom: '26px', maxWidth: '760px' }}>
                      The system first extracts text, checks whether the file belongs in this section, and then decides whether summary generation
                      can continue safely.
                    </p>

                    <input
                      id="fileInput"
                      type="file"
                      accept=".pdf,.doc,.docx,.png,.jpg,.jpeg,.txt"
                      onChange={handleFileChange}
                      style={{ display: 'none' }}
                    />

                    <div
                      style={{
                        border: '2px dashed #c2ced9',
                        borderRadius: '24px',
                        padding: '24px',
                        background: '#f7fafc',
                        marginBottom: '20px',
                      }}
                    >
                      <label
                        htmlFor="fileInput"
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '10px',
                          padding: '14px 18px',
                          borderRadius: '14px',
                          background: '#ffffff',
                          color: '#102235',
                          cursor: 'pointer',
                          border: '1px solid #d4dfe8',
                          fontWeight: 600,
                        }}
                      >
                        <IonIcon icon={documentTextOutline} />
                        Choose file
                      </label>

                      {selectedFile ? (
                        <div style={{ marginTop: '16px', color: '#36485a', lineHeight: 1.7 }}>
                          <div style={{ fontWeight: 700 }}>{selectedFile.name}</div>
                          <div style={{ color: '#6a7a89', fontSize: '14px' }}>{(selectedFile.size / 1024).toFixed(2)} KB</div>
                        </div>
                      ) : (
                        <div style={{ marginTop: '16px', color: '#6a7a89', fontSize: '14px' }}>Accepted: PDF, DOCX, TXT, PNG, JPG</div>
                      )}
                    </div>

                    <IonButton
                      onClick={handleUpload}
                      disabled={!selectedFile || uploading}
                      style={{
                        '--background': config.accent,
                        '--border-radius': '16px',
                        height: '54px',
                        fontWeight: 700,
                      }}
                    >
                      {uploading ? (
                        <>
                          <IonSpinner name="crescent" style={{ marginRight: '10px' }} />
                          Validating document...
                        </>
                      ) : (
                        'Upload and Check'
                      )}
                    </IonButton>

                    {uploadError && (
                      <div
                        style={{
                          marginTop: '20px',
                          padding: '14px 16px',
                          borderRadius: '18px',
                          background: '#fef2f2',
                          border: '1px solid #fecaca',
                          color: '#b91c1c',
                          display: 'flex',
                          gap: '10px',
                        }}
                      >
                        <IonIcon icon={closeCircleOutline} style={{ fontSize: '18px', marginTop: '2px' }} />
                        <span>{uploadError}</span>
                      </div>
                    )}
                  </div>
                ) : (
                  <>
                    <div
                      style={{
                        background: '#ffffff',
                        borderRadius: '26px',
                        border: '1px solid #d4dfe8',
                        padding: '26px',
                        boxShadow: '0 18px 40px rgba(16, 34, 53, 0.05)',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '18px', alignItems: 'start', flexWrap: 'wrap' }}>
                        <div>
                          <div
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '8px',
                              padding: '8px 12px',
                              borderRadius: '999px',
                              background: analysisResult.can_generate_summary === false ? '#fff7ef' : '#edf8f0',
                              color: analysisResult.can_generate_summary === false ? '#8a3b12' : '#166534',
                              fontWeight: 700,
                              fontSize: '12px',
                              marginBottom: '12px',
                            }}
                          >
                            <IonIcon icon={analysisResult.can_generate_summary === false ? alertCircleOutline : checkmarkCircleOutline} />
                            {analysisResult.can_generate_summary === false ? 'Section mismatch warning' : 'Document ready for summary'}
                          </div>
                          <h2 style={{ fontSize: '30px', color: '#102235', marginBottom: '8px' }}>Validation result</h2>
                          <p style={{ color: '#48576a', lineHeight: 1.75, maxWidth: '760px' }}>{analysisResult.reason}</p>
                        </div>

                        <div
                          style={{
                            padding: '12px 14px',
                            borderRadius: '16px',
                            background: `${config.accent}12`,
                            minWidth: '190px',
                          }}
                        >
                          <div style={{ color: '#6a7a89', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '4px' }}>
                            Predicted category
                          </div>
                          <div style={{ color: '#102235', fontWeight: 700 }}>{analysisResult.predicted_category}</div>
                        </div>
                      </div>

                      {isMismatched && (
                        <div
                          style={{
                            marginTop: '18px',
                            padding: '16px 18px',
                            borderRadius: '18px',
                            background: '#fff7ef',
                            border: '1px solid #f3c9ae',
                            color: '#8a3b12',
                            display: 'grid',
                            gap: '10px',
                          }}
                        >
                          <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                            <IonIcon icon={warningOutline} style={{ fontSize: '18px', marginTop: '2px' }} />
                            <div style={{ lineHeight: 1.7 }}>
                              <strong>This file does not match the selected section.</strong> {analysisResult.suggested_action}
                            </div>
                          </div>
                          {!!analysisResult.expected_documents?.length && (
                            <div style={{ display: 'grid', gap: '8px', paddingLeft: '30px' }}>
                              {analysisResult.expected_documents.map((doc) => (
                                <div key={doc} style={{ fontSize: '14px', color: '#6f3414' }}>
                                  - {doc}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}

                      {!!analysisResult._meta?.warnings?.length && (
                        <div
                          style={{
                            marginTop: '16px',
                            padding: '14px 16px',
                            borderRadius: '18px',
                            background: '#f7fafc',
                            border: '1px solid #d4dfe8',
                            color: '#48576a',
                          }}
                        >
                          <div style={{ display: 'flex', gap: '10px', alignItems: 'center', marginBottom: '8px' }}>
                            <IonIcon icon={informationCircleOutline} style={{ fontSize: '18px', color: '#0b4f6c' }} />
                            <strong>Processing notes</strong>
                          </div>
                          {analysisResult._meta.warnings.map((warning) => (
                            <div key={warning} style={{ fontSize: '14px', lineHeight: 1.7 }}>
                              {warning}
                            </div>
                          ))}
                        </div>
                      )}

                      <div style={{ display: 'flex', gap: '14px', flexWrap: 'wrap', marginTop: '22px' }}>
                        <IonButton
                          onClick={handleGenerateSummary}
                          disabled={generatingSummary || analysisResult.can_generate_summary === false}
                          style={{
                            '--background': config.accent,
                            '--border-radius': '16px',
                            height: '52px',
                            fontWeight: 700,
                          }}
                        >
                          {generatingSummary ? (
                            <>
                            <IonSpinner name="crescent" style={{ marginRight: '8px' }} />
                              Generating report...
                            </>
                          ) : (
                            <>
                              <IonIcon icon={sparklesOutline} slot="start" />
                              Generate Summary
                            </>
                          )}
                        </IonButton>

                        <IonButton
                          fill="outline"
                          onClick={() => {
                            setAnalysisResult(null);
                            setUploadError('');
                            sessionStorage.removeItem(uploadStateKey);
                          }}
                          style={{
                            '--border-radius': '16px',
                            '--border-color': '#c2ced9',
                            '--color': '#102235',
                            height: '52px',
                            fontWeight: 600,
                          }}
                        >
                          Upload Another File
                        </IonButton>
                      </div>

                      {generatingSummary && (
                        <div
                          style={{
                            marginTop: '16px',
                            padding: '14px 16px',
                            borderRadius: '18px',
                            background: '#eff4ff',
                            border: '1px solid rgba(0, 88, 190, 0.16)',
                            color: '#0b1c30',
                            display: 'flex',
                            gap: '10px',
                            alignItems: 'flex-start',
                          }}
                        >
                          <IonSpinner name="crescent" style={{ flexShrink: 0, marginTop: '2px' }} />
                          <div style={{ lineHeight: 1.7, fontSize: '14px' }}>
                            LexiNote is extracting clauses, obligations, risks, and recommendations from the document. This can take around 20 to 45 seconds depending on the provider and document size.
                          </div>
                        </div>
                      )}
                    </div>

                    <div
                      style={{
                        background: '#ffffff',
                        borderRadius: '26px',
                        border: '1px solid #d4dfe8',
                        padding: '24px',
                        boxShadow: '0 18px 40px rgba(16, 34, 53, 0.05)',
                      }}
                    >
                      <h3 style={{ fontSize: '24px', color: '#102235', marginBottom: '14px' }}>Extracted text preview</h3>
                      <div
                        style={{
                          background: '#15283a',
                          color: '#e6edf3',
                          borderRadius: '20px',
                          padding: '22px',
                          maxHeight: '520px',
                          overflowY: 'auto',
                          whiteSpace: 'pre-wrap',
                          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
                          fontSize: '13px',
                          lineHeight: 1.8,
                        }}
                      >
                        {analysisResult.extracted_text || 'No text extracted.'}
                      </div>
                    </div>
                  </>
                )}
              </div>
            </div>
          </section>
        </div>
      </IonContent>
    </IonPage>
  );
};

export default UploadPage;
