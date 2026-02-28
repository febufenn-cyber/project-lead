type Lead = {
  id: string;
  company_name: string;
  lead_score: number;
};

export function LeadTable({ leads }: { leads: Lead[] }) {
  return (
    <table>
      <thead>
        <tr>
          <th>Company</th>
          <th>Score</th>
        </tr>
      </thead>
      <tbody>
        {leads.map((lead) => (
          <tr key={lead.id}>
            <td>{lead.company_name}</td>
            <td>{lead.lead_score}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
