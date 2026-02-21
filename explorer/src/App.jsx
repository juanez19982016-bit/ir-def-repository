import { useState, useEffect, useMemo } from 'react';
import { Search, Filter, HardDrive, Music, Mic2, Tag, Check, Download, AlertCircle, Speaker, Lock, Key, X } from 'lucide-react';

const LICENSE_KEY_SECRET = "TONE-PRO-2026"; // Clave estática para clientes con acceso al Drive

// Mapeo de marcas a imágenes reales de amplificadores y equipos (Alta Calidad)
const getBrandImage = (brand) => {
    if (!brand) return 'https://images.unsplash.com/photo-1610444648792-7103ba12db63?w=500&q=80';
    const b = brand.toLowerCase();

    if (b.includes('marshall')) return 'https://images.unsplash.com/photo-1588032768007-82782b67eb54?w=500&q=80'; // Marshall Stack
    if (b.includes('fender')) return 'https://images.unsplash.com/photo-1511215443422-79f90680fd74?w=500&q=80'; // Fender Combo
    if (b.includes('orange')) return 'https://images.unsplash.com/photo-1601662998634-118cf9451996?w=500&q=80'; // Orange Amp
    if (b.includes('vox')) return 'https://images.unsplash.com/photo-1598514982205-f36b96d1e8d4?w=500&q=80'; // Vox Amp
    if (b.includes('mesa') || b.includes('boogie')) return 'https://images.unsplash.com/photo-1543884879-c5c7ce1a55f6?w=500&q=80'; // High Gain Amp
    if (b.includes('ampeg') || b.includes('bass')) return 'https://images.unsplash.com/photo-1520606412150-13f5fb470bc6?w=500&q=80'; // Bass Rack
    if (b.includes('pedal') || b.includes('boss') || b.includes('stomp')) return 'https://images.unsplash.com/photo-1510915361894-db8b60106cb1?w=500&q=80'; // Pedals
    if (b.includes('peavey') || b.includes('5150') || b.includes('evh')) return 'https://images.unsplash.com/photo-1563216178-005ca7732dc4?w=500&q=80'; // Metal Amp
    if (b.includes('engl') || b.includes('bogner') || b.includes('diezel')) return 'https://images.unsplash.com/photo-1574229550215-6bd399d863cc?w=500&q=80'; // Boutique Amp

    // Fallbacks genéricos basados en la longitud del texto
    const fallbacks = [
        'https://images.unsplash.com/photo-1610444648792-7103ba12db63?w=500&q=80', // Dark Amp
        'https://images.unsplash.com/photo-1534068590799-09895a701e3e?w=500&q=80', // Tubes / Válvulas
        'https://images.unsplash.com/photo-1582662057917-80fb05f27806?w=500&q=80', // Studio gear
        'https://images.unsplash.com/photo-1606557680650-6a3a7f8087ab?w=500&q=80', // Textura Amp
    ];
    return fallbacks[b.length % fallbacks.length];
};

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

    // Initial Load
    useEffect(() => {
        // Verificar si el usuario ya está autenticado
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

    const handleDownloadRequest = (item) => {
        if (!isAuthenticated) {
            setAuthModalOpen(true);
            return;
        }

        // Si la URL es directa de la web (HTTP), descarga normalmente.
        if (item.p.startsWith('http')) {
            window.open(item.p, '_blank');
        } else {
            // ENLACE REAL A GOOGLE DRIVE:
            // Dado que gestionas los permisos agregándolos a Drive manualmente, ellos ya tienen acceso a tu carpeta.
            // Esta función "truco" abre su Google Drive realizando una búsqueda exacta por el nombre del archivo.
            // Así, el archivo aparecerá en pantalla instantáneamente listo para ser descargado de su propio Drive autorizado.
            const driveSearchUrl = `https://drive.google.com/drive/u/0/search?q=${encodeURIComponent('"' + item.n + '"')}`;
            window.open(driveSearchUrl, '_blank');
        }
    };

    const verifyLicense = (e) => {
        e.preventDefault();
        // Lógica de validador estático (Catálogo Privado)
        if (licenseInput.trim().toUpperCase() === LICENSE_KEY_SECRET) {
            setIsAuthenticated(true);
            localStorage.setItem('toneHub_pro_access', 'true');
            setAuthModalOpen(false);
            setAuthError("");
        } else {
            setAuthError("Clave de acceso inválida o expirada.");
        }
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
                                <Check className="w-4 h-4" /> Acceso Confirmado
                            </div>
                        ) : (
                            <button onClick={() => setAuthModalOpen(true)} className="flex items-center gap-2 px-4 py-2 rounded-full bg-slate-800/80 text-slate-300 text-xs font-bold uppercase tracking-wider hover:bg-slate-700 transition-colors border border-slate-700 shadow-lg">
                                <Key className="w-4 h-4 text-emerald-400" /> Ingresar Clave
                            </button>
                        )}
                    </div>
                </div>
            </nav>

            {/* Hero Section */}
            <div className="pt-32 pb-16 px-6 max-w-[1600px] mx-auto">
                <div className="text-center max-w-3xl mx-auto mb-12 animate-slide-in">
                    <h2 className="text-4xl md:text-5xl font-extrabold text-white mb-6 tracking-tight">
                        Explora la <span className="text-gradient">Bóveda de Tono</span>
                    </h2>
                    <p className="text-slate-400 text-lg leading-relaxed">
                        Explorador y buscador oficial para acceder directamente a la base de datos más grande de impulsos IR y perfiles NAM en tu Google Drive.
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
                                onDownload={() => handleDownloadRequest(item)}
                                isAuthenticated={isAuthenticated}
                            />
                        ))
                    )}
                </div>
            </main>

            {/* MODAL PARA CLAVE DE ACCESO PRIVADA */}
            {isAuthModalOpen && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
                    <div className="absolute inset-0 bg-brand-dark/95 backdrop-blur-md" onClick={() => setAuthModalOpen(false)}></div>
                    <div className="glass-panel relative w-full max-w-md rounded-2xl overflow-hidden animate-slide-in shadow-[0_0_50px_rgba(16,185,129,0.15)] border-emerald-500/20">

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

                            <h3 className="text-3xl font-black text-white mb-2 tracking-tight">Catálogo <span className="text-gradient">Privado</span></h3>
                            <p className="text-slate-400 text-sm mb-6 leading-relaxed">
                                Debes ingresar la clave maestra proporcionada al momento de habilitarse tu acceso al servidor de Google Drive, para poder vincular y descargar los recursos.
                            </p>

                            <div className="space-y-4 pt-2">
                                <form onSubmit={verifyLicense} className="space-y-3">
                                    <div className="relative">
                                        <Key className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-emerald-400/50" />
                                        <input
                                            type="text"
                                            placeholder="Ingresa tu clave de acceso..."
                                            className="w-full bg-slate-800/80 border border-slate-700 text-white px-10 py-3 rounded-xl focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none transition-all placeholder:text-slate-500"
                                            value={licenseInput}
                                            onChange={(e) => setLicenseInput(e.target.value)}
                                            required
                                        />
                                    </div>
                                    {authError && <p className="text-red-400 text-xs font-semibold">{authError}</p>}
                                    <button type="submit" className="w-full py-3 px-4 bg-emerald-500 hover:bg-emerald-400 text-slate-950 rounded-xl font-bold flex items-center justify-center gap-2 transition-all shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/40 hover:-translate-y-0.5">
                                        Autenticar Dispositivo
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

const StatBox = ({ icon, value, label }) => (
    <div className="glass-panel p-5 rounded-2xl flex flex-col justify-center relative overflow-hidden group">
        <div className="absolute -right-4 -top-4 w-16 h-16 bg-white/5 rounded-full blur-xl group-hover:bg-emerald-500/10 transition-colors"></div>
        <div className="flex items-center justify-between mb-3 z-10">
            <div className="w-10 h-10 rounded-full bg-slate-800/80 flex items-center justify-center text-emerald-400 shadow-inner border border-slate-700/30">
                {icon}
            </div>
            <span className="text-[9px] font-bold text-emerald-500 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 uppercase tracking-widest">DRIVE</span>
        </div>
        <div className="text-3xl font-black text-white tracking-tight mb-1 z-10">{value}</div>
        <div className="text-xs font-bold text-slate-400 uppercase tracking-widest z-10">{label}</div>
    </div>
);

const ToneCard = ({ item, onDownload, isAuthenticated }) => {
    const isNam = item.t === 'NAM';
    const accentColor = isNam ? 'text-cyan-400 bg-cyan-400/20 border-cyan-400/30' : 'text-emerald-400 bg-emerald-400/20 border-emerald-400/30';
    const bgImage = getBrandImage(item.b);

    return (
        <div className="tone-card flex flex-col h-full bg-brand-card">

            <div className="h-32 p-4 relative flex flex-col justify-between overflow-hidden">
                {/* Imagen Real del Equipo (Fondo Integrado) */}
                <img src={bgImage} alt={item.b} className="absolute inset-0 w-full h-full object-cover z-0 opacity-40 group-hover:opacity-75 transition-opacity duration-500 mix-blend-screen" />
                <div className="absolute inset-0 bg-gradient-to-t from-[#0b1120] via-[#0b1120]/60 to-transparent z-0"></div>

                <div className="flex justify-between items-start relative z-10">
                    <span className={`px-2.5 py-1 rounded-md text-[10px] font-black uppercase tracking-wider border backdrop-blur-md ${accentColor}`}>
                        {item.t}
                    </span>
                </div>

                <div className="relative text-2xl font-black text-white/90 tracking-tighter w-full truncate drop-shadow-md z-10">
                    {item.b?.toUpperCase()}
                </div>
            </div>

            <div className="p-5 flex-grow flex flex-col relative z-10">
                <div className="text-[10px] font-bold text-slate-500 tracking-widest uppercase mb-1">{item.b}</div>
                <h3 className="text-white font-bold leading-snug mb-3 line-clamp-2" title={item.n}>{item.n}</h3>

                <div className="flex flex-wrap gap-1.5 mt-auto mb-5">
                    {item.tag?.slice(0, 3).map(t => (
                        <span key={t} className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 border border-slate-700/50 uppercase tracking-widest font-semibold shadow-inner">
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
                            <><Download className="w-4 h-4" /> Buscar en Drive</>
                        ) : (
                            <><Lock className="w-4 h-4 text-emerald-500/70" /> Requiere Acceso</>
                        )}
                    </button>
                    <p className="text-[9px] text-center uppercase tracking-widest text-slate-600 font-semibold">{isAuthenticated ? 'Enlace Directo' : 'Ingresa Clave Privada'}</p>
                </div>
            </div>
        </div>
    );
};

export default App;
