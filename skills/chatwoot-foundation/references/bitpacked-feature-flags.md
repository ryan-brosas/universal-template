<!-- capsule-v2 -->
# Bitpacked feature flags — how are 126 features packed into two bigint columns from one YAML source of truth?

**Source:** Chatwoot MIT `develop@6154aebcfea1fe62e8dd01fbf94568ef827fc51c`; Codebase Memory `ext-chatwoot`. **Question:** How does a multi-tenant account model carry dozens of boolean features without a migration per feature?

## YAML → FlagShihTzu bit-column boot mapping
**Path/Symbol:** `app/models/concerns/featurable.rb:Featurable` (lines 4-44 mapping, 73-103 accessors).
**Signature:** `FEATURE_LIST = YAML.safe_load(Rails.root.join('config/features.yml').read).freeze`; `FEATURE_FLAG_COLUMNS = ['feature_flags', 'feature_flags_ext_1']`; `MAX_FEATURES_PER_COLUMN = 63`.
**Data Shape:** each feature entry `{name, column?}`; column N maps feature i (1-based) to bit `feature_<name>`; QUERY_MODE `flag_query_mode: :bit_operator, check_for_column: false` enables SQL bit queries.

### Decisive source
```ruby
def self.feature_flag_mappings_for(feature_list)
  features_by_column = feature_list.group_by { |feature| feature['column'].presence || DEFAULT_FEATURE_FLAG_COLUMN }

  mappings = FEATURE_FLAG_COLUMNS.index_with do |column|
    features = features_by_column.delete(column) || []
    validate_feature_count!(column, features)

    features.each_with_index.to_h do |feature, index|
      [index + 1, "feature_#{feature['name']}".to_sym]
    end
  end

  validate_feature_columns!(features_by_column)
  mappings
end

def self.validate_feature_count!(column, features)
  return if features.size <= MAX_FEATURES_PER_COLUMN

  raise ArgumentError, "Account feature flag column #{column} supports up to #{MAX_FEATURES_PER_COLUMN} features"
end
```

**Flow:** at BOOT the concern reads config/features.yml, groups entries by target column (default `feature_flags`, overflow `feature_flags_ext_1`), validates ≤63 per bigint column and that every named column exists, then hands FlagShihTzu the generated `has_flags ... merge(QUERY_MODE)` definitions → accounts gain `feature_<name>?/enable_features!/disable_features!` plus `selected_feature_flags=` bulk writer (which unselects all first — full-replace semantics) → new accounts copy defaults from InstallationConfig `ACCOUNT_LEVEL_FEATURE_DEFAULTS` in a before_create. Enterprise-only features live in the same YAML with `column: feature_flags_ext_1`.
**Invariant:** The YAML file is the SINGLE source of truth: adding a feature is a YAML line + (when crossing 63) nothing else — but bit POSITIONS are index-derived, so reordering or removing entries silently remaps every existing account's stored bits; entries are append-only in practice. Boot-time ArgumentError beats runtime corruption: unknown column names or overfull columns refuse to start the app.
**Probe:** `grep -n 'MAX_FEATURES_PER_COLUMN = ' app/models/concerns/featurable.rb` → line 6; direct test `spec/models/concerns/featurable_spec.rb` pins all four mapping rules ("maps extension flags to feature_flags_ext_1 with independent bit positions", "raises when a flag column has more than the supported number of features").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chatwoot", query: "Featurable feature_flag_mappings_for column flags", limit: 5 });
```
Rank-1: `Featurable.feature_flag_mappings_for app/models/concerns/featurable.rb 15-29`.

## Verdict
Adopt config-file-driven bit-packing with boot-time validation and append-only position discipline when your feature count exceeds a handful. Adapt FlagShihTzu to hand-rolled bitmask scopes if avoiding the dependency. Omit cloud-side entitlement sync (InstallationConfig wiring) if flags are admin-set.
