#ifndef ROO_3DPOLYNOMIAL
#define ROO_3DPOLYNOMIAL

#include <vector>

#include "RooAbsPdf.h"
#include "RooRealProxy.h"
#include "RooListProxy.h"

#define ROO_3DPOLYNOMIAL_XCODE 2
#define ROO_3DPOLYNOMIAL_YCODE 3
#define ROO_3DPOLYNOMIAL_ZCODE 5

class RooRealVar;
class RooArgList ;

class Roo3DPolynomial : public RooAbsPdf {
public:

  Roo3DPolynomial() ;
  Roo3DPolynomial(const char* name, const char* title,
        RooAbsReal& x, RooAbsReal& y, RooAbsReal& z) ;
  Roo3DPolynomial(const char *name, const char *title,
		RooAbsReal& x, RooAbsReal& y, RooAbsReal& z,
        const RooArgList& _coefListX,
        const RooArgList& _coefListY,
        const RooArgList& _coefListZ,
        Int_t lowestOrder=1) ;

  Roo3DPolynomial(const Roo3DPolynomial& other, const char* name = 0);
  virtual TObject* clone(const char* newname) const { return new Roo3DPolynomial(*this, newname); }
  virtual ~Roo3DPolynomial() ;

  Int_t getAnalyticalIntegral(RooArgSet& allVars, RooArgSet& analVars, const char* rangeName=0) const ;
  Double_t analyticalIntegral(Int_t code, const char* rangeName=0) const ;

protected:

  RooRealProxy _x;
  RooRealProxy _y;
  RooRealProxy _z;
  RooListProxy _coefListX ;
  RooListProxy _coefListY ;
  RooListProxy _coefListZ ;
  Int_t _lowestOrder ;

  mutable std::vector<Double_t> _wksp; //! do not persist

  Double_t evaluate() const;

  ClassDef(Roo3DPolynomial,1) // Polynomial PDF
};

#endif
