import PropertyWizard from '@/components/wizard/property-wizard';

export default function NewAIVideoPage() {
    return <PropertyWizard allowedCategories={['Resale', 'Rent', 'New Development']} />;
}
