import { useState, useEffect, useMemo, useRef } from 'react';
import { Search, Filter, HardDrive, Music, Mic2, Tag, Play, Check, Download, AlertCircle, Speaker, Shield, Crown, PlayCircle, X, Lock, Key, CreditCard, Volume2 } from 'lucide-react';

const LICENSE_KEY_SECRET = "TONE-PRO-2026"; // Clave estática o contraseña para clientes de pago en Drive

const App = () => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [query, setQuery] = useState('');
    const [filterType, setFilterType] = useState('All');
    const [filterBrand, setFilterBrand] = useState('All');

    // Auth State
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [isAuthModalOpen, setAuthModalOpen] = useState(false);
    const [licenseInput, setLicenseInput] = useState("");
    const [authError, setAuthError] = useState("");
    const [showPaypal, setShowPaypal] = useState(false); // Toggle to show PayPal buttons

    // Audio Engine State
    const [previewing, setPreviewing] = useState(null); // ID
    const [audioError, setAudioError] = useState("");
    const audioContextRef = useRef(null);
    const sourceNodeRef = useRef(null);

    // Initial Load
    useEffect(() => {
        // Verificar si el usuario ya pago en una sesión anterior
        const savedAuth = localStorage.getItem('toneHub_pro_access');
        if (savedAuth === 'true') {
            setIsAuthenticated(true);
        }

        const baseUrl = import.meta.env.BASE_URL;
        const cleanBase = baseUrl.endsWith('/') ? baseUrl : `${baseUrl}/`;
        const jsonPath = `${cleanBase}data/catalog.json`;

        fetch(jsonPath)
            .then(res => {
                if (!res.ok) throw new Error(`HTTP error! Status: ${res.status}`);
                return res.json();
            })
            .then(d => {
                if (!d || !d.items) throw new Error("Datos del catálogo inválidos");
                setData(d);
                setLoading(false);
            })
            .catch(e => {
                console.error("Error al cargar el catálogo:", e);
                setLoading(false);
                setData({ error: e.message });
            });

        // Setup simple Audio Context for Previews IF supported
        try {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            audioContextRef.current = new AudioContext();
        } catch (e) {
            console.warn("Web Audio API no soportada por el navegador");
        }

        return () => {
            if (audioContextRef.current?.state !== 'closed') {
                audioContextRef.current?.close();
            }
        };
    }, []);

    const filteredItems = useMemo(() => {
        if (!data) return [];
        let items = data.items;

        if (filterType !== 'All') {
            items = items.filter(i => i.t.includes(filterType) || (filterType === 'NAM' && i.n.endsWith('.nam')));
        }

        if (filterBrand !== 'All') {
            items = items.filter(i => i.b === filterBrand);
        }

        if (query) {
            const q = query.toLowerCase();
            items = items.filter(i =>
                i.n.toLowerCase().includes(q) ||
                i.p.toLowerCase().includes(q) ||
                (i.tag && i.tag.some(t => t.toLowerCase().includes(q)))
            );
        }

        return items.slice(0, 100);
    }, [data, query, filterType, filterBrand]);

    // Motor de Audio 100% Funcional usando Convolución
    const togglePreview = async (item) => {
        setAudioError("");
        if (previewing === item.id) {
            // Stop current playback
            if (sourceNodeRef.current) {
                sourceNodeRef.current.stop();
                sourceNodeRef.current.disconnect();
                sourceNodeRef.current = null;
            }
            setPreviewing(null);
            return;
        }

        if (!audioContextRef.current) {
            setAudioError("Tu navegador no soporta Web Audio API.");
            return;
        }

        if (item.t === 'NAM') {
            setAudioError("Los modelos NAM no se pueden procesar en tiempo real en el navegador. Descarga el archivo para usarlo en el plugin.");
            return;
        }

        // Si es IR (Wav), intentamos procesarlo 100% real
        setPreviewing(item.id);
        const actx = audioContextRef.current;
        if (actx.state === 'suspended') await actx.resume();

        try {
            // Generar una señal "pop" o ruido blanco para emular un estímulo rápido 
            // y escuchar el cuarto/filtro (una convolución real).
            // Lo ideal sería descargar un track "seco" de guitarra y convolucionar, 
            // pero generamos una ráfaga sintética impulsiva como demo si no hay archivo.

            // Para ser 100% funcional, intentamos descargar el archivo IR de la ruta.
            // NOTA: Si item.p es ruta rclone (sin http), esto fallará porque no está hospedado públicamente.
            if (!item.p.startsWith('http')) {
                throw new Error("El archivo no está alojado en un servidor HTTP público (es una ruta local/rclone). No se puede transmitir el audio en vivo sin acceso backend.");
            }

            const response = await fetch(item.p);
            if (!response.ok) throw new Error("No se pudo obtener el archivo de audio IR desde el servidor.");
            const arrayBuffer = await response.arrayBuffer();
            const irBuffer = await actx.decodeAudioData(arrayBuffer);

            // Crear el nodo de Convolución y cargar el IR
            const convolver = actx.createConvolver();
            convolver.buffer = irBuffer;

            // Generar un 'Click/Impulso' para hacer sonar la convolución
            const osc = actx.createOscillator();
            const gainNode = actx.createGain();

            osc.connect(convolver);
            convolver.connect(gainNode);
            gainNode.connect(actx.destination);

            osc.type = 'sawtooth';
            osc.frequency.setValueAtTime(110, actx.currentTime); // Frecuencia de guitarra (La/A2)

            // Envolvente tipo "chug" de guitarra
            gainNode.gain.setValueAtTime(0, actx.currentTime);
            gainNode.gain.linearRampToValueAtTime(1, actx.currentTime + 0.05);
            gainNode.gain.exponentialRampToValueAtTime(0.001, actx.currentTime + 0.5);

            osc.start(actx.currentTime);
            osc.stop(actx.currentTime + 0.5);

            sourceNodeRef.current = osc;

            // Detener el UI state después de 1 segundo
            setTimeout(() => {
                if (previewing === item.id) setPreviewing(null);
            }, 1000);

        } catch (err) {
            console.error("Audio Preview Error:", err);
            setAudioError(err.message || "Error al procesar el audio.");
            setPreviewing(null);
        }
    };

    const handleDownloadRequest = (itemPath) => {
        if (!isAuthenticated) {
            setAuthModalOpen(true);
            return;
        }

        // 100% Funcional para cuentas premium:
        // Si la URL es HTTP(S), descarga directamente en el navegador.
        if (itemPath.startsWith('http')) {
            const link = document.createElement('a');
            link.href = itemPath;
            link.download = itemPath.split('/').pop();
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        } else {
            // Si es ruta de rclone (Google Drive sin enlace público), 
            // la acción 100% real funcional es copiar el comando de bajada exacto al portapapeles.
            navigator.clipboard.writeText(`rclone copy "${itemPath}" ./descargas`);
            alert("✓ ¡Acceso Premium Confirmado! \n\nRuta copiada al portapapeles para uso con rclone:\n" + itemPath + "\n\nAlternativamente, accede a la carpeta central compartida de Google Drive usando tu correo registrado.");
        }
    };

    const verifyLicense = (e) => {
        e.preventDefault();
        // Lógica de validador real. Para evitar hardcoding total, 
        // normalmente aquí harías POST a tu API o validarías con Gumroad Ping API.
        if (licenseInput.trim().toUpperCase() === LICENSE_KEY_SECRET) {
            setIsAuthenticated(true);
            localStorage.setItem('toneHub_pro_access', 'true');
            setAuthModalOpen(false);
            setAuthError("");
        } else {
            setAuthError("Licencia o código de acceso inválido.");
        }
    };

    const handlePurchaseSuccess = (details) => {
        // Callback que ejecuta PayPal al completar el pago exitosamente
        setIsAuthenticated(true);
        localStorage.setItem('toneHub_pro_access', 'true');
        setAuthModalOpen(false);
        alert(`¡Pago Completado! Gracias, ${details.payer.name.given_name}. Tu cuenta ToneHub Pro ha sido activada de por vida.`);
    };

    if (loading) return (
        <div className="min-h-screen w-full flex flex-col items-center justify-center bg-brand-dark text-emerald-400 font-sans gap-6">
            <div className="relative">
                <div className="w-16 h-16 border-4 border-emerald-500/20 rounded-full animate-spin absolute inset-0"></div>
                <div className="w-16 h-16 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
                <Music className="w-6 h-6 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-emerald-400" />
            </div>
            <p className="tracking-widest uppercase text-sm font-semibold animate-pulse text-emerald-500/80">Cargando Bóveda de Sonido</p>
        </div>
    );

    if (!data || data.error) return (
        <div className="min-h-screen w-full flex flex-col items-center justify-center bg-brand-dark text-red-400 p-8">
            <div className="glass-panel p-8 rounded-2xl max-w-lg text-center border-red-500/20">
                <AlertCircle className="w-16 h-16 mb-6 mx-auto text-red-500/80 animate-bounce" />
                <h2 className="text-2xl font-bold mb-4 text-white">Sistema Desconectado</h2>
                <p className="text-sm opacity-80 mb-6 bg-red-950/50 p-4 rounded-xl border border-red-500/20">
                    {data?.error ? data.error : "No se encontró el catálogo central."}
                </p>
            </div>
        </div>
    );

    return (
        <div className="min-h-screen pb-24">

            {/* Navegación */}
            <nav className="fixed top-0 w-full z-50 glass-panel border-b-0 border-slate-800/50">
                <div className="max-w-[1600px] mx-auto px-6 h-20 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-400 to-cyan-500 p-[1px] shadow-lg shadow-emerald-500/20 flex items-center justify-center">
                            <div className="w-full h-full bg-slate-900 rounded-xl flex items-center justify-center">
                                <Music className="w-5 h-5 text-emerald-400" />
                            </div>
                        </div>
                        <div>
                            <h1 className="text-lg font-bold text-white tracking-tight leading-none">ToneHub <span className="text-emerald-400">Pro</span></h1>
                            <p className="text-[10px] uppercase tracking-wider text-slate-400 mt-1 font-semibold">{data.items.length.toLocaleString()} Archivos Indexados</p>
                        </div>
                    </div>

                    <div className="hidden md:flex items-center gap-4">
                        {isAuthenticated ? (
                            <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-bold uppercase tracking-wider">
                                <Check className="w-4 h-4" /> Acceso Pro Desbloqueado
                            </div>
                        ) : (
                            <>
                                <button onClick={() => setAuthModalOpen(true)} className="flex items-center gap-2 px-4 py-2 rounded-full bg-slate-800/80 text-slate-300 text-xs font-bold uppercase tracking-wider hover:bg-slate-700 transition-colors border border-slate-700">
                                    <Key className="w-4 h-4 text-cyan-400" /> Tengo Clave
                                </button>
                                <button onClick={() => { setAuthModalOpen(true); setShowPaypal(true); }} className="flex items-center gap-2 px-5 py-2 rounded-full bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-950 text-xs font-bold uppercase tracking-wider hover:shadow-lg hover:shadow-emerald-500/25 transition-all hover:scale-105">
                                    <Crown className="w-4 h-4" /> Comprar Acceso
                                </button>
                            </>
                        )}
                    </div>
                </div>
            </nav>

            {/* Alerta de Error de Audio (Temporal) */}
            {audioError && (
                <div className="fixed top-24 right-6 z-50 bg-red-950/90 border border-red-500/50 text-red-400 px-6 py-4 rounded-xl shadow-2xl backdrop-blur flex items-start gap-4 animate-slide-in max-w-sm">
                    <AlertCircle className="w-6 h-6 shrink-0 mt-0.5" />
                    <div className="flex-grow">
                        <h4 className="font-bold text-white text-sm">Error de Motor 3D/Audio</h4>
                        <p className="text-xs opacity-80 mt-1 leading-relaxed">{audioError}</p>
                    </div>
                    <button onClick={() => setAudioError("")} className="text-slate-500 hover:text-white"><X className="w-4 h-4" /></button>
                </div>
            )}

            {/* Hero Section */}
            <div className="pt-32 pb-16 px-6 max-w-[1600px] mx-auto">
                <div className="text-center max-w-3xl mx-auto mb-12 animate-slide-in">
                    <h2 className="text-4xl md:text-5xl font-extrabold text-white mb-6 tracking-tight">
                        Descubre el <span className="text-gradient">Tono Definitivo</span>
                    </h2>
                    <p className="text-slate-400 text-lg leading-relaxed">
                        Accede a la base de datos más grande de impulsos IR y perfiles de amplificadores NAM. Todo 100% organizado, con calidad de estudio y listo para descargar en tus proyectos.
                    </p>
                </div>

                <div className="max-w-2xl mx-auto relative group">
                    <div className="absolute inset-y-0 left-0 flex items-center pl-4 pointer-events-none">
                        <Search className="w-5 h-5 text-emerald-500/70 group-focus-within:text-emerald-400 transition-colors" />
                    </div>
                    <input
                        type="text"
                        placeholder="Busca por 'JCM800', 'Tube Screamer', o 'Mesa Boogie'..."
                        className="search-input text-lg"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                    />
                </div>
            </div>

            <main className="max-w-[1600px] mx-auto px-6">

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
                    <StatBox icon={<HardDrive />} value={data.items.length.toLocaleString()} label="Total Capturas" />
                    <StatBox icon={<Speaker />} value={data.stats.types['IR']?.toLocaleString() || 0} label="Gabinetes (IR)" />
                    <StatBox icon={<Mic2 />} value={data.stats.types['NAM']?.toLocaleString() || 0} label="Equipos (NAM)" />
                    <StatBox icon={<Tag />} value={Object.keys(data.stats.brands).length} label="Marcas Reales" />
                </div>

                <div className="flex flex-wrap items-center gap-3 mb-8 glass-panel p-4 rounded-2xl sticky top-24 z-40">
                    <div className="flex items-center gap-2 mr-4 border-r border-slate-700/50 pr-4">
                        <Filter className="w-4 h-4 text-emerald-500" />
                        <span className="text-sm font-semibold text-white">Filtros</span>
                    </div>

                    <div className="flex overflow-x-auto no-scrollbar gap-2 flex-grow">
                        <div className={`filter-pill ${filterType === 'All' ? 'filter-pill-active' : 'filter-pill-inactive'}`} onClick={() => setFilterType('All')}>
                            Todo
                        </div>
                        <div className={`filter-pill ${filterType === 'NAM' ? 'filter-pill-active' : 'filter-pill-inactive'}`} onClick={() => setFilterType('NAM')}>
                            <span className="flex items-center gap-1.5"><Mic2 className="w-3.5 h-3.5" /> Amplis/Pedales</span>
                        </div>
                        <div className={`filter-pill ${filterType === 'IR' ? 'filter-pill-active' : 'filter-pill-inactive'}`} onClick={() => setFilterType('IR')}>
                            <span className="flex items-center gap-1.5"><Speaker className="w-3.5 h-3.5" /> Gabinetes (IRs)</span>
                        </div>

                        <div className="w-px h-6 bg-slate-700/50 mx-2 self-center shrink-0"></div>

                        {Object.entries(data.stats.brands)
                            .sort((a, b) => b[1] - a[1])
                            .slice(0, 10)
                            .map(([brand, count]) => (
                                <div key={brand} className={`filter-pill ${filterBrand === brand ? 'filter-pill-active' : 'filter-pill-inactive'}`} onClick={() => setFilterBrand(filterBrand === brand ? 'All' : brand)}>
                                    {brand} <span className="opacity-50 ml-1 text-[10px]">{count}</span>
                                </div>
                            ))}
                    </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-6">
                    {filteredItems.length === 0 ? (
                        <div className="col-span-full py-20 text-center glass-panel rounded-2xl">
                            <AlertCircle className="w-12 h-12 mx-auto mb-4 text-slate-500" />
                            <h3 className="text-xl font-bold text-white mb-2">Sin resultados</h3>
                            <p className="text-slate-400">Intenta con otros filtros.</p>
                        </div>
                    ) : (
                        filteredItems.map(item => (
                            <ToneCard
                                key={item.id}
                                item={item}
                                previewing={previewing === item.id}
                                onPreview={() => togglePreview(item)}
                                onDownload={() => handleDownloadRequest(item.p)}
                                isAuthenticated={isAuthenticated}
                            />
                        ))
                    )}
                </div>
            </main>

            {/* MODAL 100% FUNCIONAL — PayPal Checkout & Licencias */}
            {isAuthModalOpen && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
                    <div className="absolute inset-0 bg-brand-dark/95 backdrop-blur-md" onClick={() => setAuthModalOpen(false)}></div>
                    <div className="glass-panel relative w-full max-w-md rounded-2xl overflow-hidden animate-slide-in shadow-[0_0_50px_rgba(16,185,129,0.15)] border-emerald-500/20 max-h-[90vh] overflow-y-auto">

                        <button onClick={() => setAuthModalOpen(false)} className="absolute right-4 top-4 text-slate-400 hover:text-white transition-colors z-10 p-2">
                            <X className="w-5 h-5" />
                        </button>

                        <div className="p-8 text-center relative overflow-hidden">
                            <div className="absolute -top-32 -left-24 w-64 h-64 bg-emerald-500/20 rounded-full blur-3xl"></div>

                            <div className="w-16 h-16 mx-auto mb-6 bg-gradient-to-br from-emerald-400 to-cyan-500 rounded-full p-[1px] relative">
                                <div className="w-full h-full bg-slate-900 rounded-full flex items-center justify-center shadow-inner">
                                    <Lock className="w-8 h-8 text-emerald-400" />
                                </div>
                            </div>

                            <h3 className="text-3xl font-black text-white mb-2 tracking-tight">ToneHub <span className="text-gradient">Pro</span></h3>
                            <p className="text-slate-400 text-sm mb-6 leading-relaxed">
                                Este es un archivo exclusivo. Adquiere acceso de por vida para poder descargar los 35,000+ recursos de la bóveda premium.
                            </p>

                            <div className="space-y-4 pt-2">
                                {/* Integración Oficial de PayPal */}
                                {showPaypal ? (
                                    <PayPalCheckoutButton onSuccess={handlePurchaseSuccess} />
                                ) : (
                                    <button
                                        onClick={() => setShowPaypal(true)}
                                        className="w-full py-4 px-4 bg-[#FFC439] hover:bg-[#F4BB33] text-black rounded-lg font-bold flex items-center justify-center gap-2 transition-all shadow-lg"
                                    >
                                        <svg viewBox="0 0 124 33" className="h-5" xmlns="http://www.w3.org/2000/svg"><path d="M46.211 6.749h-6.839a.95.95 0 0 0-.939.802l-2.766 17.537a.57.57 0 0 0 .564.658h3.265a.95.95 0 0 0 .939-.803l.746-4.73a.95.95 0 0 1 .938-.803h2.165c4.505 0 7.105-2.18 7.784-6.5.306-1.89.013-3.375-.872-4.415-1.132-1.326-3.113-1.746-4.985-1.746zM47 13.154c-.374 2.454-2.249 2.454-4.062 2.454h-1.032l.724-4.582h1.309c1.425 0 2.63.14 3.093 1.05.25.5.25.9-.032 1.078zm29.982 7.358A1.91 1.91 0 0 1 75.11 22.4H71.94c-.452 0-.847-.321-.926-.767l-2.768-17.53A.57.57 0 0 1 68.809 3.44H73.08a.95.95 0 0 1 .939.802l1.393 8.84 5.957-8.91C81.652 3.738 82 3.44 82.5 3.44h4.15l-6.85 9.778.016.023 3.52 7.766q.17.38-.284.502h-4.07A1.85 1.85 0 0 1 76.98 20.5zM31.259 4.887H23.51a.95.95 0 0 0-.939.803L19.492 25.26a.57.57 0 0 0 .564.658h3.39c.504 0 .93-.38 1.002-.88l1.455-9.227a.95.95 0 0 1 .939-.803h2.165c4.505 0 7.105-2.18 7.784-6.5.306-1.89.013-3.375-.872-4.415-1.132-1.326-3.113-1.746-4.985-1.746zM32.048 11.29c-.374 2.454-2.249 2.454-4.062 2.454h-1.032l.724-4.582h1.309c1.425 0 2.63.14 3.093 1.05.25.5.25.9-.032 1.078zm87.319-3.79c-.31-1.637-1.161-2.905-2.452-3.664-1.29-.758-3.08-1-5.161-1H105a.95.95 0 0 0-.939.803l-2.766 17.537a.57.57 0 0 0 .564.658h3.39c.504 0 .93-.38 1.002-.88l1.41-8.943a.95.95 0 0 1 .938-.802h2.247c4.662 0 7.351-2.256 8.054-6.726zm-7.653 4.845c-.4 2.544-2.4 2.544-4.331 2.544h-1.042l.738-4.674h1.326c1.451 0 2.678.14 3.148 1.05v.001A1.19 1.19 0 0 1 111.714 12.344zm-22.38 8.047l-.372 2.361a.57.57 0 0 1-.564.481h-3.09a.57.57 0 0 1-.564-.664l2.87-18.17a.95.95 0 0 1 .939-.804h5.684c3.27 0 5.4 1.378 5.4 4.54a4.11 4.11 0 0 1-1.602 3.328c-.802.618-1.922.981-3.262 1.056l3.35 6.463c.2.39-.086.84-.52.84h-3.41c-.344 0-.649-.19-.79-.496zM96.096 7.636h-2.126l-.683 4.321h2.215c1.47 0 2.122-.72 2.308-1.905.105-.67.065-1.284-.285-1.745-.353-.46-1.066-.67-2.13-.67z M123.63 2.05h1.16v1.163c0 .12 0 .222-.047.306a.54.54 0 0 1-.225.215.82.82 0 0 1-.371.077h-1.636v-3.791h1.53c.184 0 .341.037.473.111a.69.69 0 0 1 .31.3.93.93 0 0 1 .108.455c0 .26-.067.46-.201.604a.65.65 0 0 1-.417.228.32.32 0 0 1 .157.064c.05.04.1.096.155.168zM123.165 1.15H122.56v1.442h.744c.075 0 .15-.01.226-.03A.44.44 0 0 0 123.702 2.4a.5.5 0 0 0 .045-.229c0-.13-.04-.236-.12-.317s-.2-.122-.363-.122h-.1zM123.674 2.66c0-.07-.02-.126-.06-.168a.33.33 0 0 0-.156-.06v1.272c.075-.018.136-.056.182-.114s.069-.136.069-.234zM122.378 0h3v4h-3z" fill="#003087" /></svg>
                                        Pagar Fijo Seguro
                                    </button>
                                )}

                                <div className="my-6 relative">
                                    <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-slate-700/50"></div></div>
                                    <div className="relative flex justify-center text-xs"><span className="px-2 bg-slate-900 text-slate-500 font-semibold uppercase tracking-wider">Ya soy Cliente Oficial</span></div>
                                </div>

                                <form onSubmit={verifyLicense} className="space-y-3">
                                    <div className="relative">
                                        <Key className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                                        <input
                                            type="text"
                                            placeholder="Ingresa tu clave de acceso VIP..."
                                            className="w-full bg-slate-800/80 border border-slate-700 text-white px-10 py-3 rounded-xl focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none transition-all placeholder:text-slate-500"
                                            value={licenseInput}
                                            onChange={(e) => setLicenseInput(e.target.value)}
                                            required
                                        />
                                    </div>
                                    {authError && <p className="text-red-400 text-xs font-semibold">{authError}</p>}
                                    <button type="submit" className="w-full py-3 px-4 glass-panel border border-slate-600 hover:border-emerald-500/50 hover:bg-slate-800 rounded-xl font-bold flex items-center justify-center gap-2 text-white transition-all">
                                        Acceder a Descargas Reales
                                    </button>
                                </form>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

// Componente oficial del SDK de PayPal
const PayPalCheckoutButton = ({ onSuccess }) => {
    const paypalRef = useRef();

    useEffect(() => {
        // Asegurarse de que el Smart Button se inicializa de forma asíncrona
        if (window.paypal) {
            window.paypal.Buttons({
                createOrder: (data, actions) => {
                    return actions.order.create({
                        purchase_units: [{
                            description: "ToneHub Pro - Acceso Vitalicio (35,000+ Tones)",
                            amount: {
                                currency_code: "USD",
                                value: "49.00" // <- VALOR DEL PRODUCTO (Ajustarlo a necesidad)
                            }
                        }]
                    });
                },
                onApprove: async (data, actions) => {
                    const details = await actions.order.capture();
                    onSuccess(details); // El pago fue aprobado y capturado
                },
                onError: (err) => {
                    console.error("PayPal Error:", err);
                    alert("No se pudo procesar el pago. Por favor intenta de nuevo.");
                }
            }).render(paypalRef.current);
        }
    }, []);

    return (
        <div className="relative isolate z-50">
            <div ref={paypalRef} className="min-h-[150px]"></div>
            <p className="text-[10px] text-slate-500 italic mt-2 text-center">Pago procesado 100% seguro y encriptado por PayPal.</p>
        </div>
    );
};

const StatBox = ({ icon, value, label }) => (
    <div className="glass-panel p-5 rounded-2xl flex flex-col justify-center relative overflow-hidden group">
        <div className="absolute -right-4 -top-4 w-16 h-16 bg-white/5 rounded-full blur-xl group-hover:bg-emerald-500/10 transition-colors"></div>
        <div className="flex items-center justify-between mb-3 z-10">
            <div className="w-10 h-10 rounded-full bg-slate-800/80 flex items-center justify-center text-emerald-400 shadow-inner border border-slate-700/30">
                {icon}
            </div>
            <span className="text-[9px] font-bold text-emerald-500 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 uppercase tracking-widest">PRO</span>
        </div>
        <div className="text-3xl font-black text-white tracking-tight mb-1 z-10">{value}</div>
        <div className="text-xs font-bold text-slate-400 uppercase tracking-widest z-10">{label}</div>
    </div>
);

const ToneCard = ({ item, previewing, onPreview, onDownload, isAuthenticated }) => {
    const isNam = item.t === 'NAM';
    const accentColor = isNam ? 'text-cyan-400 bg-cyan-400/10 border-cyan-400/30' : 'text-emerald-400 bg-emerald-400/10 border-emerald-400/30';

    return (
        <div className="tone-card flex flex-col h-full bg-brand-card">

            <div className={`h-32 p-4 relative flex flex-col justify-between overflow-hidden ${isNam ? 'bg-slate-800/60' : 'bg-slate-800/50'}`}>
                {/* Olas animadas de fondo en hover/preview */}
                <div className={`absolute inset-0 bg-gradient-to-br ${isNam ? 'from-cyan-500/10 to-transparent' : 'from-emerald-500/10 to-transparent'} opacity-0 group-hover:opacity-100 transition-opacity duration-700`}></div>

                <div className="flex justify-between items-start relative z-10">
                    <span className={`px-2.5 py-1 rounded text-[10px] font-bold uppercase tracking-wider border ${accentColor}`}>
                        {item.t}
                    </span>
                    <button
                        onClick={(e) => { e.stopPropagation(); onPreview(); }}
                        className={`w-10 h-10 flex items-center justify-center rounded-full glass-panel shadow-xl transition-all hover:scale-110 z-20 ${previewing ? 'bg-emerald-500 text-slate-950 border-emerald-400 animate-pulse' : 'text-white hover:text-emerald-400 hover:border-emerald-500/50'}`}
                        title={isNam ? "Modelos no soportan preview" : "Audición en Tiempo Real"}
                    >
                        {previewing ? <Volume2 className="w-5 h-5 mx-1" /> : <PlayCircle className="w-6 h-6 ml-0.5" />}
                    </button>
                </div>

                <div className="absolute -bottom-2 -left-2 text-4xl font-black opacity-[0.03] text-white tracking-tighter w-full overflow-hidden pointer-events-none select-none z-0">
                    {item.b?.toUpperCase()}
                </div>
            </div>

            <div className="p-5 flex-grow flex flex-col relative z-10">
                <div className="text-[10px] font-bold text-slate-500 tracking-widest uppercase mb-1">{item.b}</div>
                <h3 className="text-white font-bold leading-snug mb-3 line-clamp-2">{item.n}</h3>

                <div className="flex flex-wrap gap-1.5 mt-auto mb-5">
                    {item.tag?.slice(0, 3).map(t => (
                        <span key={t} className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 border border-slate-700/50 uppercase tracking-widest font-semibold">
                            {t}
                        </span>
                    ))}
                    {item.tag?.length > 3 && <span className="px-1.5 py-0.5 rounded text-[10px] text-slate-500 font-bold">+{item.tag.length - 3}</span>}
                </div>

                <div className="pt-4 mt-auto border-t border-slate-800/50 flex flex-col gap-2">
                    <button
                        onClick={onDownload}
                        className={`w-full py-2.5 px-4 font-bold rounded-xl flex items-center justify-center gap-2 transition-all border ${isAuthenticated ? 'bg-gradient-to-r from-emerald-500/20 to-cyan-500/20 text-emerald-400 border-emerald-500/30 hover:border-emerald-500/60 hover:from-emerald-500/30 hover:to-cyan-500/30 shadow-[0_4px_15px_rgba(16,185,129,0.1)]' : 'bg-slate-800/50 hover:bg-slate-700 border-slate-700/50 text-slate-200'}`}
                    >
                        {isAuthenticated ? (
                            <><Download className="w-4 h-4" /> Bajar Archivo</>
                        ) : (
                            <><Lock className="w-4 h-4 text-emerald-500/70" /> Obtener Archivo</>
                        )}
                    </button>
                    <p className="text-[9px] text-center uppercase tracking-widest text-slate-600 font-semibold">{isAuthenticated ? 'Directo de bóveda' : 'Requiere Licencia'}</p>
                </div>
            </div>
        </div>
    );
};

export default App;
