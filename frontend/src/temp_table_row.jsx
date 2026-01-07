candidates.map((c, i) => (
    <tr key={i} className="hover:bg-purple-50/40 transition-all duration-200 group cursor-default">
        {/* Candidate Name & Email */}
        <td className="px-8 py-5">
            <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-100 to-blue-100 flex items-center justify-center text-purple-600 font-bold shadow-inner">
                    {(c['Candidate Name'] || c['Name'] || '?')[0].toUpperCase()}
                </div>
                <div>
                    <p className="font-semibold text-gray-900">{c['Candidate Name'] || c['Name'] || 'N/A'}</p>
                    <p className="text-xs text-gray-500">{c['Email'] || 'No email'}</p>
                </div>
            </div>
        </td>

        {/* Role */}
        <td className="px-8 py-5">
            <span className="bg-gray-100 text-gray-700 px-3 py-1 rounded-lg text-xs font-semibold">
                {selectedJob || 'N/A'}
            </span>
        </td>

        {/* Phone */}
        <td className="px-8 py-5">
            <span className="text-gray-600 font-mono text-sm">
                {c['Phone'] || c['Contact'] || 'N/A'}
            </span>
        </td>

        {/* Status */}
        <td className="px-8 py-5">
            <span className="inline-flex items-center gap-1.5 text-blue-700 bg-blue-50 px-3 py-1.5 rounded-full text-xs font-bold border border-blue-100 shadow-sm">
                <Clock size={14} />
                Imported
            </span>
        </td>

        {/* Resume Link */}
        <td className="px-8 py-5 text-right">
            {c['Resume Link'] ? (
                <a
                    href={c['Resume Link']}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-purple-600 hover:text-purple-700 font-semibold text-sm hover:underline inline-flex items-center gap-1"
                >
                    View Resume
                    <ArrowRight size={14} />
                </a>
            ) : (
                <span className="text-gray-400 text-sm">No link</span>
            )}
        </td>
    </tr>
))
