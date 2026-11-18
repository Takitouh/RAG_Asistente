import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ChatContainer } from '../components/chat/ChatContainer';
import { ChatInput } from '../components/chat/ChatInput';
import { CitationCard } from '../components/citations/CitationCard';
import { ChatMessage } from '../components/chat/ChatMessage';
import { AbstentionAlert } from '../components/chat/AbstentionAlert';
import { ChatMessageItem, Citation, NormativeVersion } from '../types';

const mockActiveVersion: NormativeVersion = {
  id: 'uts_tg_2019',
  document_id: 'doc_1',
  nombre: 'Reglamento de Trabajo de Grado 2019',
  numero_acuerdo: 'Acuerdo 01-002',
  anio: 2019,
  fecha_expedicion: '2019-03-15',
  estado_vigencia: 'Vigente',
  status: 'PROCESADO',
  status_message: 'Indexado exitosamente',
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  activated_at: '2026-01-01T00:00:00Z',
  report_json: null,
  chunks_count: 181,
};

const mockCitation: Citation = {
  chunk_id: 'chk_101',
  version_id: 'uts_tg_2019',
  document_id: 'doc_1',
  document_name: 'reglamento_trabajo_grado.pdf',
  capitulo_numero: 2,
  capitulo_romano: 'II',
  capitulo_titulo: 'De las Modalidades',
  articulo_numero: 14,
  articulo_ordinal: '14°',
  paragrafo_numero: '1',
  inciso_marker: null,
  page_start: 12,
  page_end: 12,
  location_hint: 'Capítulo II, Artículo 14, Parágrafo 1',
  texto_fragmento: 'Las modalidades aprobadas de trabajo de grado en las UTS son: Proyecto de investigación, Práctica empresarial y Monografía.',
};

describe('Chat Components & RAG Flow Tests', () => {
  it('1. ChatInput: usuario puede escribir y enviar preguntas con Enter o botón', async () => {
    const handleSend = vi.fn();
    render(
      <ChatInput
        onSendMessage={handleSend}
        isLoading={false}
        hasActiveVersion={true}
        activeVersionName={mockActiveVersion.nombre}
      />
    );

    const textarea = screen.getByLabelText(/campo de pregunta sobre el reglamento/i);
    const sendButton = screen.getByLabelText(/enviar pregunta/i);

    expect(sendButton).toBeDisabled();

    // Escribir pregunta
    fireEvent.change(textarea, { target: { value: '¿Cuáles son las modalidades de grado?' } });
    expect(sendButton).not.toBeDisabled();

    // Enviar haciendo clic
    fireEvent.click(sendButton);
    expect(handleSend).toHaveBeenCalledWith('¿Cuáles son las modalidades de grado?');
  });

  it('2. ChatInput: no permite envíos duplicados o mientras está cargando', () => {
    const handleSend = vi.fn();
    render(
      <ChatInput
        onSendMessage={handleSend}
        isLoading={true}
        hasActiveVersion={true}
      />
    );

    const textarea = screen.getByLabelText(/campo de pregunta sobre el reglamento/i);
    const sendButton = screen.getByLabelText(/enviar pregunta/i);

    expect(textarea).toBeDisabled();
    expect(sendButton).toBeDisabled();
  });

  it('3. ChatMessage: renderiza respuestas del asistente y del usuario correctamente', () => {
    const userMsg: ChatMessageItem = {
      id: '1',
      sender: 'user',
      text: 'Pregunta del estudiante',
      timestamp: new Date().toISOString(),
    };

    const { rerender } = render(<ChatMessage message={userMsg} />);
    expect(screen.getByText('Pregunta del estudiante')).toBeInTheDocument();

    const asstMsg: ChatMessageItem = {
      id: '2',
      sender: 'assistant',
      text: 'Respuesta sustentada con la normativa UTS.',
      timestamp: new Date().toISOString(),
      version_id: 'uts_tg_2019',
      document_name: 'Reglamento 2019',
      latency_ms: 1200,
    };

    rerender(<ChatMessage message={asstMsg} />);
    expect(screen.getByText('Respuesta sustentada con la normativa UTS.')).toBeInTheDocument();
    expect(screen.getByText(/Reglamento: Reglamento 2019/i)).toBeInTheDocument();
    expect(screen.getByText('1.20s')).toBeInTheDocument();
  });

  it('4. CitationCard: muestra metadatos normativos y expande fragmento de evidencia', async () => {
    render(<CitationCard citation={mockCitation} index={0} />);

    // Verifica que se muestre el resumen de ubicación
    expect(screen.getByText(/Capítulo II • Art\. 14 • Parágrafo 1/i)).toBeInTheDocument();
    expect(screen.getByText(/Pág\. 12/i)).toBeInTheDocument();

    // El fragmento no está visible antes de expandir
    expect(screen.queryByText(/Las modalidades aprobadas de trabajo de grado/i)).not.toBeInTheDocument();

    // Clic en la tarjeta para expandir
    fireEvent.click(screen.getByText(/Capítulo II • Art\. 14 • Parágrafo 1/i));

    // Ahora el texto normativo exacto debe estar presente
    expect(screen.getByText(/Las modalidades aprobadas de trabajo de grado/i)).toBeInTheDocument();
    expect(screen.getByText(/Texto Normativo Verificado/i)).toBeInTheDocument();
  });

  it('5. AbstentionAlert: muestra claramente la abstención por falta de evidencia', () => {
    render(
      <AbstentionAlert
        reason="No se encontraron artículos normativos aplicables en el reglamento 2019."
        messageText="El asistente no dispone de evidencia suficiente para esta consulta."
      />
    );

    expect(screen.getByText(/Abstención Normativa/i)).toBeInTheDocument();
    expect(screen.getByText(/Evidencia Insuficiente/i)).toBeInTheDocument();
    expect(screen.getByText(/El asistente no dispone de evidencia suficiente/i)).toBeInTheDocument();
    expect(screen.getByText(/No se encontraron artículos normativos aplicables/i)).toBeInTheDocument();
  });

  it('6. ChatMessage con Error Técnico: distingue visualmente error de abstención', () => {
    const errorMsg: ChatMessageItem = {
      id: 'err_1',
      sender: 'assistant',
      text: 'Error al conectar con el servidor backend FastAPI.',
      timestamp: new Date().toISOString(),
      error: true,
    };

    render(<ChatMessage message={errorMsg} />);
    expect(screen.getByText(/Error Técnico de Comunicación/i)).toBeInTheDocument();
    expect(screen.getByText(/Error al conectar con el servidor backend/i)).toBeInTheDocument();
  });

  it('7. ChatContainer: muestra banner de cambio de versión normativa si ocurre durante la sesión', () => {
    const handleDismiss = vi.fn();
    render(
      <ChatContainer
        messages={[]}
        isLoading={false}
        activeVersion={mockActiveVersion}
        onSelectPrompt={vi.fn()}
        versionChangedWarning="El administrador activó una nueva normativa: Reglamento 2021."
        onDismissVersionWarning={handleDismiss}
      />
    );

    expect(screen.getByText(/El administrador activó una nueva normativa: Reglamento 2021/i)).toBeInTheDocument();
    const btn = screen.getByText(/Entendido/i);
    fireEvent.click(btn);
    expect(handleDismiss).toHaveBeenCalled();
  });
});
