export type CategoryKey = 'citizen' | 'business' | 'student';

export interface CategoryConfig {
  key: CategoryKey;
  title: string;
  subtitle: string;
  badge: string;
  department: string;
  accent: string;
  surface: string;
  uploadTitle: string;
  uploadHint: string;
  supportedDocs: string[];
  warning: string;
}

export const CATEGORY_CONFIG: Record<CategoryKey, CategoryConfig> = {
  citizen: {
    key: 'citizen',
    title: 'Citizen Documents',
    subtitle: 'Personal legal papers for housing, finance, notice, property, and everyday civil matters.',
    badge: 'Citizen',
    department: 'Citizen Legal Help Desk',
    accent: '#0b6b57',
    surface: '#f3fbf8',
    uploadTitle: 'Upload a citizen legal document',
    uploadHint: 'Use this section only for personal agreements, notices, deeds, housing records, or individual legal paperwork.',
    supportedDocs: [
      'Rental agreement',
      'Loan agreement',
      'Legal notice',
      'Property document',
      'Insurance document',
    ],
    warning: 'Only personal or citizen-side legal records are accepted here. Business and student files should be uploaded in their own section.',
  },
  business: {
    key: 'business',
    title: 'Business Documents',
    subtitle: 'Commercial contracts, vendor papers, internal agreements, and operational records.',
    badge: 'Business',
    department: 'Business Compliance Desk',
    accent: '#0b4f6c',
    surface: '#f2f8fc',
    uploadTitle: 'Upload a business or commercial document',
    uploadHint: 'Use this section only for vendor agreements, service contracts, NDAs, invoices, policies, or other commercial documents.',
    supportedDocs: [
      'Vendor agreement',
      'NDA',
      'Service contract',
      'Invoice',
      'Partnership agreement',
    ],
    warning: 'Only business or commercial records are accepted here. Citizen and student documents should be moved to their correct section before analysis.',
  },
  student: {
    key: 'student',
    title: 'Student Documents',
    subtitle: 'Academic and training records such as internship, admission, scholarship, and university papers.',
    badge: 'Student',
    department: 'Student Rights & Records Desk',
    accent: '#8a3b12',
    surface: '#fff7f1',
    uploadTitle: 'Upload a student or academic document',
    uploadHint: 'Use this section only for academic or training records like internship letters, admission letters, scholarship notices, certificates, and university communications.',
    supportedDocs: [
      'Internship offer letter',
      'Admission letter',
      'Scholarship letter',
      'University notice',
      'Academic certificate',
    ],
    warning: 'Only academic or student records are accepted here. If the document belongs to citizen or business use, summary generation will be blocked with a warning.',
  },
};
