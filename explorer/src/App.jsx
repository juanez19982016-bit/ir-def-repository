import { useState, useEffect, useMemo } from 'react';
import { Search, Filter, HardDrive, Music, Mic2, Tag, Play, Check, Download, AlertCircle } from 'lucide-react';

const App = () => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [query, setQuery] = useState('');
    const [filterType, setFilterType] = useState('All');
    const [filterBrand, setFilterBrand] = useState('All');
    const [copied, setCopied] = useState(null);

    useEffect(() => {
        fetch('./data/catalog.json')
            .then(res => res.json())
            .then(d => {
                setData(d);
                setLoading(false);
            })
            .catch(e => {
                console.error("Failed to load catalog", e);
                setLoading(false);
            });
    }, []);

    const filteredItems = useMemo(() => {
        if (!data) return [];
        let items = data.items;

        // Type Filter
        if (filterType !== 'All') {
            items = items.filter(i => i.t.includes(filterType) || (filterType === 'NAM' && i.n.endsWith('.nam')));
        }

        // Brand Filter
        if (filterBrand !== 'All') {
            items = items.filter(i => i.b === filterBrand);
        }

        // Text Search
        if (query) {
            const q = query.toLowerCase();
            items = items.filter(i =>
                i.n.toLowerCase().includes(q) ||
                i.p.toLowerCase().includes(q) ||
                (i.tag && i.tag.some(t => t.toLowerCase().includes(q)))
            );
        }

        return items.slice(0, 500); // Limit render for perf
    }, [data, query, filterType, filterBrand]);

    const copyPath = (path) => {
        navigator.clipboard.writeText(path);
        setCopied(path);
        setTimeout(() => setCopied(null), 2000);
    };

    if (loading) return <div className="h-screen flex items-center justify-center text-emerald-400 text-xl font-mono animate-pulse">Initializing Tone Explorer...</div>;
    if (!data) return <div className="h-screen flex items-center justify-center text-red-500 font-mono">Error: Catalog not found. Run workflow first.</div>;

    return (
        <div className="min-h-screen bg-gray-950 text-gray-200 font-sans selection:bg-emerald-900 selection:text-white pb-20">
            {/* Header */}
            <header className="border-b border-gray-800 bg-gray-900/50 backdrop-blur sticky top-0 z-50">
                <div className="max-w-7xl mx-auto px-4 py-4 flex flex-col md:flex-row items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
                            <Music className="w-6 h-6 text-emerald-400" />
                        </div>
                        <div>
                            <h1 className="text-xl font-bold text-white tracking-tight">Tone Explorer <span className="text-emerald-500 text-sm font-mono ml-2">v3.0</span></h1>
                            <p className="text-xs text-gray-400">Indexed {data.items.length.toLocaleString()} files • {data.updated}</p>
                        </div>
                    </div>

                    <div className="flex items-center gap-2 w-full md:w-auto relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                        <input
                            type="text"
                            placeholder="Search amp, cab, mic..."
                            className="w-full md:w-80 bg-gray-900 border border-gray-800 rounded-full pl-10 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all placeholder-gray-600"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                        />
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="max-w-7xl mx-auto px-4 py-8 space-y-8">

                {/* Stats Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <StatCard icon={<HardDrive />} label="Total Files" value={data.items.length.toLocaleString()} color="text-blue-400" />
                    <StatCard icon={<Music />} label="Guitar IRs" value={data.stats.types['IR']?.toLocaleString() || 0} color="text-purple-400" />
                    <StatCard icon={<Mic2 />} label="NAM Models" value={data.stats.types['NAM']?.toLocaleString() || 0} color="text-amber-400" />
                    <StatCard icon={<Tag />} label="Brands" value={Object.keys(data.stats.brands).length} color="text-pink-400" />
                </div>

                {/* Filters */}
                <div className="flex flex-wrap gap-2 pb-2 overflow-x-auto no-scrollbar">
                    <FilterButton active={filterType === 'All'} onClick={() => setFilterType('All')}>All Types</FilterButton>
                    <FilterButton active={filterType === 'NAM'} onClick={() => setFilterType('NAM')}>NAM Models</FilterButton>
                    <FilterButton active={filterType === 'IR'} onClick={() => setFilterType('IR')}>Impulse Responses</FilterButton>
                    <div className="w-px h-6 bg-gray-800 mx-2 self-center"></div>
                    {Object.entries(data.stats.brands)
                        .sort((a, b) => b[1] - a[1]) // Sort by count
                        .slice(0, 8)
                        .map(([brand, count]) => (
                            <FilterButton key={brand} active={filterBrand === brand} onClick={() => setFilterBrand(filterBrand === brand ? 'All' : brand)}>
                                {brand} <span className="opacity-50 text-xs ml-1">{count}</span>
                            </FilterButton>
                        ))}
                </div>

                {/* Results Table */}
                <div className="bg-gray-900/50 border border-gray-800 rounded-xl overflow-hidden shadow-2xl">
                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm">
                            <thead className="bg-gray-900 text-gray-400 uppercase text-xs font-semibold tracking-wider">
                                <tr>
                                    <th className="px-6 py-4">Name</th>
                                    <th className="px-6 py-4">Brand</th>
                                    <th className="px-6 py-4">Type</th>
                                    <th className="px-6 py-4">Path / Action</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-800">
                                {filteredItems.length === 0 ? (
                                    <tr>
                                        <td colSpan="4" className="px-6 py-12 text-center text-gray-500">
                                            <AlertCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
                                            No results found matching your criteria.
                                        </td>
                                    </tr>
                                ) : (
                                    filteredItems.map(item => (
                                        <tr key={item.id} className="hover:bg-gray-800/50 transition-colors group">
                                            <td className="px-6 py-3 font-medium text-white flex items-center gap-3">
                                                <div className={`w-2 h-2 rounded-full ${item.t === 'NAM' ? 'bg-amber-500' : 'bg-purple-500'}`}></div>
                                                {item.n}
                                                {item.tag?.map(t => (
                                                    <span key={t} className="px-1.5 py-0.5 rounded text-[10px] bg-gray-800 text-gray-400 border border-gray-700">{t}</span>
                                                ))}
                                            </td>
                                            <td className="px-6 py-3 text-gray-400">{item.b}</td>
                                            <td className="px-6 py-3 text-gray-400">
                                                <span className={`px-2 py-1 rounded text-xs font-medium ${item.t === 'NAM' ? 'bg-amber-500/10 text-amber-500' : 'bg-purple-500/10 text-purple-400'}`}>
                                                    {item.t}
                                                </span>
                                            </td>
                                            <td className="px-6 py-3 text-gray-500 font-mono text-xs flex items-center gap-2">
                                                <button
                                                    onClick={() => copyPath(item.p)}
                                                    className="p-1.5 hover:bg-gray-700 rounded text-gray-400 hover:text-white transition-colors relative"
                                                    title="Copy full path for rclone"
                                                >
                                                    {copied === item.p ? <Check className="w-4 h-4 text-emerald-500" /> : <Download className="w-4 h-4" />}
                                                </button>
                                                <span className="truncate max-w-[200px] opacity-60 group-hover:opacity-100 transition-opacity select-all">{item.p}</span>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                    <div className="px-6 py-4 bg-gray-900 border-t border-gray-800 text-xs text-center text-gray-500">
                        Showing {filteredItems.length} of {data.items.length} files
                    </div>
                </div>

            </main>
        </div>
    );
};

const StatCard = ({ icon, label, value, color }) => (
    <div className="bg-gray-900/50 border border-gray-800 p-4 rounded-xl flex items-center gap-4 hover:border-gray-700 transition-colors">
        <div className={`p-3 bg-gray-800 rounded-lg ${color} bg-opacity-10`}>
            {React.cloneElement(icon, { className: `w-5 h-5 ${color}` })}
        </div>
        <div>
            <p className="text-xs text-gray-500 uppercase font-semibold">{label}</p>
            <p className="text-xl font-bold text-white">{value}</p>
        </div>
    </div>
);

const FilterButton = ({ active, children, onClick }) => (
    <button
        onClick={onClick}
        className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all flex items-center ${active ? 'bg-emerald-500 text-black shadow-lg shadow-emerald-500/20' : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white'}`}
    >
        {children}
    </button>
);

export default App;
