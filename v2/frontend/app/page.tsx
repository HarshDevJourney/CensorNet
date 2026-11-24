import Hero from "@/components/home/Hero";
import SourceChoice from "@/components/home/SourceChoice";
import HowItWorks from "@/components/home/HowItWorks";
import ArchitecturePreview from "@/components/home/ArchitecturePreview";

export default function Home() {
  return (
    <div className="space-y-20">
      <Hero />
      <SourceChoice />
      <HowItWorks />
      <ArchitecturePreview />
    </div>
  );
}
