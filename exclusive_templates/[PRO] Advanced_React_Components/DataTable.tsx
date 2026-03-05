"use client";

import React, { useState, useMemo } from 'react';

// Highly requested developer component: A data table with sorting, global search, 
// pagination, and CSV/Excel export without heavy libraries.

export default function AdvancedDataTable({
    data = [],
    columns = [],
    rowsPerPage = 10
}) {
    const [search, setSearch] = useState('');
    const [sortConfig, setSortConfig] = useState({ key: null, direction: 'ascending' });
    const [currentPage, setCurrentPage] = useState(1);

    // Memoized Search & Sort
    const processedData = useMemo(() => {
        let sortedData = [...data];

        // 1. Global Search Filter
        if (search) {
            sortedData = sortedData.filter(row =>
                Object.values(row).some(
                    val => String(val).toLowerCase().includes(search.toLowerCase())
                )
            );
        }

        // 2. Sorting
        if (sortConfig.key !== null) {
            sortedData.sort((a, b) => {
                if (a[sortConfig.key] < b[sortConfig.key]) return sortConfig.direction === 'ascending' ? -1 : 1;
                if (a[sortConfig.key] > b[sortConfig.key]) return sortConfig.direction === 'ascending' ? 1 : -1;
                return 0;
            });
        }

        return sortedData;
    }, [data, sortConfig, search]);

    // Pagination Logic
    const totalPages = Math.ceil(processedData.length / rowsPerPage);
    const paginatedData = processedData.slice((currentPage - 1) * rowsPerPage, currentPage * rowsPerPage);

    const handleSort = (key) => {
        let direction = 'ascending';
        if (sortConfig.key === key && sortConfig.direction === 'ascending') {
            direction = 'descending';
        }
        setSortConfig({ key, direction });
    };

    // Export to CSV function (Saves devs 2 hours of figuring out Blob URLs)
    const exportToCSV = () => {
        const csvRows = [];
        const headers = columns.map(col => col.header);
        csvRows.push(headers.join(','));

        processedData.forEach(row => {
            const values = columns.map(col => {
                const value = row[col.accessor];
                return `"${String(value).replace(/"/g, '""')}"`; // Escape quotes
            });
            csvRows.push(values.join(','));
        });

        const csvData = new Blob([csvRows.join('\n')], { type: 'text/csv' });
        const csvUrl = URL.createObjectURL(csvData);
        const link = document.createElement('a');
        link.href = csvUrl;
        link.download = `data_export_${new Date().toISOString().slice(0, 10)}.csv`;
        link.click();
    };

    return (
        <div className="w-full bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg shadow-sm overflow-hidden">
            {/* Table Header Controls */}
            <div className="p-4 border-b border-zinc-200 dark:border-zinc-800 flex justify-between items-center bg-zinc-50 dark:bg-zinc-900/50">
                <input
                    type="text"
                    placeholder="Search all columns..."
                    className="px-4 py-2 border border-zinc-300 dark:border-zinc-700 rounded-md bg-white dark:bg-zinc-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-64"
                    value={search}
                    onChange={(e) => { setSearch(e.target.value); setCurrentPage(1); }}
                />
                <button
                    onClick={exportToCSV}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-md transition-colors shadow-sm flex items-center gap-2"
                >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
                    Export CSV
                </button>
            </div>

            {/* Responsive Table Wrapper */}
            <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-zinc-600 dark:text-zinc-400">
                    <thead className="text-xs uppercase bg-zinc-50 dark:bg-zinc-900/50 text-zinc-500 dark:text-zinc-400 border-b border-zinc-200 dark:border-zinc-800">
                        <tr>
                            {columns.map((col) => (
                                <th key={col.accessor} className="px-6 py-3 font-medium tracking-wider cursor-pointer hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors" onClick={() => handleSort(col.accessor)}>
                                    <div className="flex items-center gap-2">
                                        {col.header}
                                        {sortConfig.key === col.accessor && (
                                            <span className="text-blue-500">{sortConfig.direction === 'ascending' ? '▲' : '▼'}</span>
                                        )}
                                    </div>
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {paginatedData.length > 0 ? paginatedData.map((row, index) => (
                            <tr key={index} className="bg-white dark:bg-zinc-900 border-b border-zinc-100 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors">
                                {columns.map(col => (
                                    <td key={col.accessor} className="px-6 py-4 whitespace-nowrap">
                                        {col.cell ? col.cell(row[col.accessor], row) : row[col.accessor]}
                                    </td>
                                ))}
                            </tr>
                        )) : (
                            <tr><td colSpan={columns.length} className="px-6 py-8 text-center text-zinc-500">No results found for "{search}"</td></tr>
                        )}
                    </tbody>
                </table>
            </div>

            {/* Pagination Footer */}
            <div className="p-4 border-t border-zinc-200 dark:border-zinc-800 flex items-center justify-between bg-zinc-50 dark:bg-zinc-900/50">
                <span className="text-sm text-zinc-500">
                    Showing {((currentPage - 1) * rowsPerPage) + 1} to {Math.min(currentPage * rowsPerPage, processedData.length)} of {processedData.length} entries
                </span>
                <div className="flex gap-2">
                    <button
                        disabled={currentPage === 1}
                        onClick={() => setCurrentPage(prev => prev - 1)}
                        className="px-3 py-1 border border-zinc-300 dark:border-zinc-700 rounded-md text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-zinc-100 dark:hover:bg-zinc-800"
                    >
                        Prev
                    </button>
                    <button
                        disabled={currentPage === totalPages || totalPages === 0}
                        onClick={() => setCurrentPage(prev => prev + 1)}
                        className="px-3 py-1 border border-zinc-300 dark:border-zinc-700 rounded-md text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-zinc-100 dark:hover:bg-zinc-800"
                    >
                        Next
                    </button>
                </div>
            </div>
        </div>
    );
}
