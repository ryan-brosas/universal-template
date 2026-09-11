<!-- capsule-v2 -->
# Per-server message DB — how do you shard mail storage per customer while hand-rolling SQL safely?

**Source:** postal MIT `main@d038eaa8c763d3cafa797ccd6f773d53470bd336`; Codebase Memory `ext-postal`. **Question:** How does Postal isolate each server's high-volume data into its own MySQL database, and how does the raw SQL builder resist injection?

## Postal::MessageDB::Database
**Path/Symbol:** `lib/postal/message_db/database.rb` (database_name :335–337, insert_raw_message :121–140, select :149–186, select_with_pagination :188–202, update :204–221, insert :223–235, escape :297–310, hash_to_sql :352–381, escape_identifier :385–391, query_on_connection :319–334); schema `lib/postal/message_db/migrations/`.
**Signature:** `Database.new(organization_id, server_id)`; `select(table, where:, order:, direction:, fields:, limit:, offset:, count:) → Array|Integer`; `insert(table, attributes) → id`.
**Data Shape:** one MySQL DB per server: `postal-server-<id>` with `messages, deliveries, live_stats, links, clicks, loads, stats, spam_checks, suppressions, webhook_signatures/webhook_requests, migrations, raw-YYYY-MM-DD` (headers+body rows). Every query fully-qualifies `` `db`.`table` ``.

### Decisive source
```ruby
def database_name
  @database_name ||= "#{Postal::Config.message_db.database_name_prefix}-server-#{@server_id}"
end

# identifiers are escaped by DOUBLING backticks — a hostile key stays ONE identifier
def escape_identifier(identifier)
  "`" + identifier.to_s.gsub("`", "``") + "`"
end
# spec: select("messages", where: { "id`=0 OR 1=1#" => "x" }) raises Mysql2::Error
# (injected key becomes a non-existent column, not SQL)

def hash_to_sql(hash, joiner = ", ")
  hash.map do |key, value|
    column = escape_identifier(key)
    if value.is_a?(Array) && value.all? { |v| v.is_a?(Integer) } then "#{column} IN (#{value.join(', ')})"
    elsif value.is_a?(Array)   then "#{column} IN (#{value.map { |v| escape(v) }.join(', ')})"
    elsif value.is_a?(Hash)
      value.each_with_object([]) do |(op, v), sql|     # :less_than/:greater_than/:*_or_equal_to only
        sql << "#{column} < #{escape(v)}" if op == :less_than      # …closed operator set
      end.join(joiner)
    else "#{column} = #{escape(value)}"
    end
  end.join(joiner)
end

def insert_raw_message(data, date = Time.now.utc.to_date)
  table_name = raw_table_name_for_date(date)          # strftime("raw-%Y-%m-%d")
  begin
    headers, body = data.split(/\r?\n\r?\n/, 2)
    headers_id = insert(table_name, data: headers)    # header and body are SEPARATE rows…
    body_id = insert(table_name, data: body)
  rescue Mysql2::Error => e
    raise unless e.message =~ /doesn't exist/
    provisioner.create_raw_table(table_name)          # …lazy daily-table provisioning via retry
    retry
  end
  [table_name, headers_id, body_id]
end

# query_on_connection: any SELECT/UPDATE/DELETE slower than 50 ms gets an EXPLAIN pretty-printed
if time > 0.05 && query =~ /\A(SELECT|UPDATE|DELETE) /
  explain_result = ResultForExplainPrinter.new(connection.query("EXPLAIN #{query}"))
  ActiveRecord::ConnectionAdapters::MySQL::ExplainPrettyPrinter.new.pp(explain_result, time)…
end
```

**Flow:** control-plane Rails DB holds organizations/servers/credentials; all message traffic goes through this class against the per-server DB chosen by `server_id`. Values go through `escape` (true→1, false→0, nil/""→NULL, else mysql-escaped literal); identifiers through backtick-doubling; hash operators form a CLOSED set (`less_than/greater_than/…`) — anything unrecognized is silently dropped from the clause (an empty operator hash yields the neutral `1=1`). Raw messages split headers/body at the first blank line into two rows of a daily table created on demand.
**Invariant:** the builder's safety does NOT come from prepared statements — it comes from doubling backticks on every identifier and mysql-escaping every value, plus never interpolating user input into the closed operator set. Schema versioning is per-server-DB (`migrations` row max version, missing-table ⇒ version 0), so provisioning can bring new servers up independently.
**Probe:** `spec/lib/postal/message_db/database_spec.rb:18–76` (backtick wrap/double/coerce; injection-neutralizing equality/IN/operator keys; end-to-end hostile-key select raises Mysql2::Error); deterministic probe executed this pass re-derived escaping.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-postal", query: "MessageDB Database escape_identifier hash_to_sql insert_raw_message", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt per-tenant schema sharding for high-volume append-mostly data, the daily-partitioned raw store with create-on-miss retry, header/body row split, slow-query EXPLAIN logging, and identifier-doubling + closed-operator-set query building when you must hand-roll SQL. Adapt MySQL specifics (backticks, `ON DUPLICATE KEY`) to your engine's quoting. Omit the migration file inventory.
