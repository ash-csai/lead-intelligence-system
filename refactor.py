import os
import glob

exclude_files = ['base.html', 'dashboard.html', 'leads.html']

replacements = {
    'class="form-control"': 'class="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white transition-colors"',
    'class="form-select"': 'class="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white transition-colors appearance-none"',
    'class="btn btn-primary"': 'class="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg shadow-sm transition-colors text-sm"',
    'class="btn btn-success"': 'class="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-medium rounded-lg shadow-sm transition-colors text-sm"',
    'class="btn btn-warning"': 'class="px-5 py-2.5 bg-amber-500 hover:bg-amber-600 text-white font-medium rounded-lg shadow-sm transition-colors text-sm"',
    'class="btn btn-danger"': 'class="px-5 py-2.5 bg-rose-600 hover:bg-rose-700 text-white font-medium rounded-lg shadow-sm transition-colors text-sm"',
    'class="btn btn-secondary"': 'class="px-5 py-2.5 bg-slate-600 hover:bg-slate-700 text-white font-medium rounded-lg shadow-sm transition-colors text-sm"',
    'class="btn btn-sm': 'class="px-3 py-1.5 text-xs',
    'class="card"': 'class="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden"',
    'class="card-body"': 'class="p-6"',
    'class="card-header"': 'class="px-6 py-4 border-b border-slate-200 bg-slate-50 font-semibold text-slate-800"',
    'class="list-group"': 'class="divide-y divide-slate-100 bg-white rounded-xl shadow-sm border border-slate-200"',
    'class="list-group-item"': 'class="p-4 hover:bg-slate-50 transition-colors"',
    'class="badge bg-primary"': 'class="px-2.5 py-0.5 rounded text-xs font-bold bg-indigo-100 text-indigo-800"',
    'class="badge bg-success"': 'class="px-2.5 py-0.5 rounded text-xs font-bold bg-emerald-100 text-emerald-800"',
    'class="badge bg-warning"': 'class="px-2.5 py-0.5 rounded text-xs font-bold bg-amber-100 text-amber-800"',
    'class="badge bg-danger"': 'class="px-2.5 py-0.5 rounded text-xs font-bold bg-rose-100 text-rose-800"',
    'class="badge bg-secondary"': 'class="px-2.5 py-0.5 rounded text-xs font-bold bg-slate-100 text-slate-800"',
    'class="badge bg-dark"': 'class="px-2.5 py-0.5 rounded text-xs font-bold bg-slate-800 text-white"',
    'class="table table-striped"': 'class="w-full text-left border-collapse text-sm"',
    'class="table"': 'class="w-full text-left border-collapse text-sm"',
    '<thead>': '<thead class="bg-slate-50 border-b border-slate-200 text-xs font-semibold text-slate-500 uppercase tracking-wider">',
    '<tbody>': '<tbody class="divide-y divide-slate-100 text-slate-700">',
    '<tr>': '<tr class="hover:bg-slate-50 transition-colors">',
    '<th>': '<th class="px-6 py-4">',
    '<td>': '<td class="px-6 py-4">',
    '<h2>': '<h2 class="text-2xl font-bold text-slate-900 mb-6 tracking-tight">',
    '<h3>': '<h3 class="text-xl font-bold text-slate-800 mb-4 tracking-tight">',
    '<h4>': '<h4 class="text-lg font-semibold text-slate-800 mb-3 tracking-tight">',
    '<h5>': '<h5 class="text-md font-semibold text-slate-800 mb-2">',
}

def update_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = content
    for old, new in replacements.items():
        new_content = new_content.replace(old, new)
        
    # Wrap tables manually
    if '<table' in new_content and '<div class="overflow-x-auto' not in new_content:
        new_content = new_content.replace('<table', '<div class="overflow-x-auto bg-white rounded-xl shadow-sm border border-slate-200 mb-6"><table')
        new_content = new_content.replace('</table>', '</table></div>')
        
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {filepath}")

os.chdir("d:\\Malik\\Lead Intelligence System - Copy\\templates")
for file in glob.glob("*.html"):
    if file not in exclude_files:
        update_file(file)
