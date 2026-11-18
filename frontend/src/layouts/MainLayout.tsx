import React from 'react';
import { Outlet } from 'react-router-dom';
import { Navbar } from '../components/ui/Navbar';
import { Footer } from '../components/ui/Footer';
import { useActiveVersion } from '../hooks/useActiveVersion';

export const MainLayout: React.FC = () => {
  const { activeVersion, isLoading: isLoadingVersion } = useActiveVersion();

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-800">
      <Navbar activeVersion={activeVersion} isLoadingVersion={isLoadingVersion} />
      <main className="flex-1 flex flex-col">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
};
